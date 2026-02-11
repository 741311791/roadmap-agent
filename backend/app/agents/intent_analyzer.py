"""
Intent Analyzer Agent（需求分析师）
"""
import re
import uuid
from app.agents.base import BaseAgent
from app.models.domain import (
    UserRequest, 
    IntentAnalysisOutput, 
    LanguagePreferences,
)
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class IntentAnalyzerAgent(BaseAgent):
    """
    需求分析师 Agent
    
    配置从环境变量加载：
    - ANALYZER_PROVIDER: 模型提供商（默认: openai）
    - ANALYZER_MODEL: 模型名称（默认: gpt-4o-mini）
    - ANALYZER_BASE_URL: 自定义 API 端点（可选）
    - ANALYZER_API_KEY: API 密钥（必需）
    """
    
    def __init__(
        self,
        agent_id: str = "intent_analyzer",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.ANALYZER_PROVIDER,
            model_name=model_name or settings.ANALYZER_MODEL,
            base_url=base_url or settings.ANALYZER_BASE_URL,
            api_key=api_key or settings.ANALYZER_API_KEY,
            temperature=0.3,
            max_tokens=8000,  # 增加 token 限制以容纳完整的 full_analysis_data
        )
    
    async def execute(self, input_data: UserRequest) -> IntentAnalysisOutput:
        """
        分析用户学习需求
        
        Args:
            input_data: 用户请求
            
        Returns:
            结构化的需求分析结果
        """
        user_request = input_data
        prefs = user_request.preferences
        
        logger.info(
            "intent_analysis_started",
            user_id=user_request.user_id,
            learning_goal=prefs.learning_goal[:50] + "..." if len(prefs.learning_goal) > 50 else prefs.learning_goal,
            current_level=prefs.current_level,
            available_hours=prefs.available_hours_per_week,
        )
        
        # 获取语言偏好
        language_prefs = prefs.get_language_preferences()
        
        # 构建用户画像信息（包含双语偏好）
        user_profile = None
        if prefs.industry or prefs.current_role or prefs.tech_stack or language_prefs:
            user_profile = {
                "industry": prefs.industry,
                "current_role": prefs.current_role,
                "tech_stack": prefs.tech_stack or [],
                "primary_language": language_prefs.primary_language,
                "secondary_language": language_prefs.secondary_language,
                # 向后兼容
                "preferred_language": language_prefs.primary_language,
            }
        
        # 加载 System Prompt
        logger.debug("intent_analysis_loading_prompt", template="intent_analyzer.j2")
        system_prompt = self._load_system_prompt(
            "intent_analyzer.j2",
            agent_name="Intent Analyzer",
            role_description="分析用户的学习需求，提取关键技术栈、难度画像和时间约束，为后续设计提供结构化输入。结合用户画像和语言偏好进行个性化分析。",
            user_goal=prefs.learning_goal,
            available_hours_per_week=prefs.available_hours_per_week,
            motivation=prefs.motivation,
            current_level=prefs.current_level,
            career_background=prefs.career_background,
            content_preference=prefs.content_preference,
            user_profile=user_profile,
            language_preferences=language_prefs.model_dump(),
        )
        
        # 构建用户消息
        profile_info = ""
        if user_profile:
            profile_parts = []
            if user_profile.get("industry"):
                profile_parts.append(f"**所属行业**: {user_profile['industry']}")
            if user_profile.get("current_role"):
                profile_parts.append(f"**当前职位**: {user_profile['current_role']}")
            if user_profile.get("tech_stack"):
                tech_list = [f"{t.get('technology', '')}({t.get('proficiency', '')})" for t in user_profile["tech_stack"]]
                profile_parts.append(f"**已掌握技术**: {', '.join(tech_list)}")
            if profile_parts:
                profile_info = "\n" + "\n".join(profile_parts)
        
        # 构建语言偏好信息
        language_info = f"\n**主要语言**: {language_prefs.primary_language}"
        if language_prefs.secondary_language and language_prefs.secondary_language != language_prefs.primary_language:
            language_info += f"\n**次要语言**: {language_prefs.secondary_language}"
        
        user_message = f"""
请分析以下用户的学习需求：

**学习目标**: {prefs.learning_goal}
**每周可投入时间**: {prefs.available_hours_per_week} 小时
**学习动机**: {prefs.motivation}
**当前水平**: {prefs.current_level}
**职业背景**: {prefs.career_background}
**内容偏好**: {", ".join(prefs.content_preference)}{profile_info}{language_info}
{"**期望完成时间**: " + str(prefs.target_deadline) if prefs.target_deadline else ""}
{f"**额外信息**: {user_request.additional_context}" if user_request.additional_context else ""}

请结合用户画像和语言偏好进行个性化分析，提取关键技术栈、难度画像、时间约束、技能差距分析，并给出个性化学习建议。
请以 JSON 格式返回结果，严格遵循输出 Schema。

**重要**：请确保输出 full_analysis_data 字段（约束文本字典），包含所有分析维度的约束信息。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        logger.info(
            "intent_analysis_calling_llm",
            user_id=user_request.user_id,
            model=self.model_name,
            provider=self.model_provider,
            primary_language=language_prefs.primary_language,
            secondary_language=language_prefs.secondary_language,
        )
        
        # 使用 instructor 的结构化输出（自动验证和重试）
        result = await self._call_llm(
            messages=messages,
            response_model=IntentAnalysisOutput
        )
        
        # 生成唯一的 roadmap_id（使用 Python UUID 确保唯一性）
        result.roadmap_id = self._generate_unique_roadmap_id(prefs.learning_goal)
        
        logger.info(
            "roadmap_id_generated",
            roadmap_id=result.roadmap_id,
            learning_goal=prefs.learning_goal[:50],
        )
        
        # 确保 language_preferences 被正确设置（LLM 可能不返回或返回格式不对）
        if not result.language_preferences:
            # 使用用户输入的语言偏好
            result.language_preferences = language_prefs
        else:
            # 验证并补充 LLM 返回的语言偏好
            if not result.language_preferences.resource_ratio:
                result.language_preferences.resource_ratio = language_prefs.get_effective_ratio()
        
        # 确保 full_analysis_data 字段不为空（如果 LLM 未输出，则使用默认值）
        if not result.full_analysis_data:
            logger.warning(
                "full_analysis_data_missing_from_llm_using_default",
                user_id=user_request.user_id,
            )
            result.full_analysis_data = {}
        
        logger.info(
            "intent_analysis_completed",
            user_id=user_request.user_id,
            roadmap_id=result.roadmap_id,
            parsed_goal=result.parsed_goal,
            key_technologies_count=len(result.key_technologies) if result.key_technologies else 0,
            difficulty_profile=result.difficulty_profile,
            primary_language=result.language_preferences.primary_language if result.language_preferences else None,
            secondary_language=result.language_preferences.secondary_language if result.language_preferences else None,
            constraints_count=len(result.full_analysis_data),
        )
        
        return result
    
    def _generate_unique_roadmap_id(self, learning_goal: str) -> str:
        """
        生成唯一的 roadmap_id
        
        格式: <英文语义短语>-<8位UUID>
        
        Args:
            learning_goal: 学习目标
            
        Returns:
            唯一的 roadmap_id
        """
        # 提取关键词并转换为英文语义短语
        # 这里使用简单的规则：保留字母、数字，替换空格为连字符，转小写
        semantic_part = re.sub(r'[^a-zA-Z0-9\s-]', '', learning_goal.lower())
        semantic_part = re.sub(r'\s+', '-', semantic_part.strip())
        
        # 限制长度（最多40个字符）
        if len(semantic_part) > 40:
            semantic_part = semantic_part[:40].rstrip('-')
        
        # 如果为空，使用默认值
        if not semantic_part:
            semantic_part = "learning-roadmap"
        
        # 生成8位 UUID 后缀
        unique_suffix = uuid.uuid4().hex[:8]
        
        roadmap_id = f"{semantic_part}-{unique_suffix}"
        
        logger.debug(
            "roadmap_id_generation_details",
            learning_goal=learning_goal,
            semantic_part=semantic_part,
            unique_suffix=unique_suffix,
            final_roadmap_id=roadmap_id,
        )
        
        return roadmap_id
