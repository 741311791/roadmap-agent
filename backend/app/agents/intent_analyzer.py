"""
Intent Analyzer Agent（需求分析师）
"""
import json
import re
import uuid
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from app.agents.base import BaseAgent
from app.models.domain import (
    IntentAnalysisOutput,
    LanguagePreferences,
    UserRequest,
)
from app.tools.registry import ToolRegistry
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
    
    可选工具支持：
    - 注入 ToolRegistry 后自动启用 web_search + ReAct 分析
    - 优先采用“一阶段直出 + 本地校验”，解析失败时才回退到第二阶段结构化提取
    - 未注入时降级为单阶段结构化输出（向后兼容）
    """
    
    def __init__(
        self,
        agent_id: str = "intent_analyzer",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        tavily_key: Optional[str] = None,
        tool_registry: Optional[ToolRegistry] = None,
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
        
        # 预分配的 Tavily API Key
        self._tavily_key = tavily_key
        
        # 注入 ToolRegistry（可选，未注入时降级为无工具模式）
        self.tool_registry = tool_registry

    def _parse_phase1_structured_output(self, raw_text: str) -> IntentAnalysisOutput:
        """
        解析第一阶段直出的结构化结果。

        设计说明：
        - ReAct 模式下，模型最终响应已经被 prompt 明确要求“直接输出 JSON”
        - 对 Gemini 来说，再额外走一次结构化提取容易触发长度截断
        - 因此优先在本地解析第一阶段结果，只有解析失败时才回退到第二阶段提取

        Args:
            raw_text: 第一阶段模型原始输出文本

        Returns:
            解析并校验后的 IntentAnalysisOutput

        Raises:
            ValueError: 文本中未找到可解析的 JSON
            ValidationError: JSON 结构不符合 IntentAnalysisOutput
        """
        cleaned_text = raw_text.strip()
        candidate_payloads: list[str] = []

        if cleaned_text:
            candidate_payloads.append(cleaned_text)

        # 兼容模型把 JSON 包在 markdown code block 中的情况。
        code_block_match = re.search(
            r"```(?:json)?\s*(\{.*\})\s*```",
            cleaned_text,
            flags=re.DOTALL,
        )
        if code_block_match:
            candidate_payloads.append(code_block_match.group(1).strip())

        # 兼容模型在 JSON 前后附带解释文本的情况。
        json_object_match = re.search(r"(\{.*\})", cleaned_text, flags=re.DOTALL)
        if json_object_match:
            candidate_payloads.append(json_object_match.group(1).strip())

        seen_payloads: set[str] = set()
        last_error: Exception | None = None

        for candidate in candidate_payloads:
            if not candidate or candidate in seen_payloads:
                continue
            seen_payloads.add(candidate)

            try:
                return IntentAnalysisOutput.model_validate(json.loads(candidate))
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc

        raise ValueError(
            "第一阶段输出未能解析为 IntentAnalysisOutput"
        ) from last_error
    
    def _get_tools_definition(self) -> List[Dict[str, Any]]:
        """
        获取工具定义列表（仅包含 web_search）
        
        Returns:
            OpenAI function calling 格式的工具 Schema 列表，
            tool_registry 未注入时返回空列表
        """
        if not self.tool_registry:
            return []
        
        all_schemas = self.tool_registry.get_all_schemas(format="openai")
        
        # 意图分析只需要 web_search，过滤掉其他工具
        return [s for s in all_schemas if s.get("function", {}).get("name") == "web_search"]
    
    async def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any]
    ) -> Any:
        """
        执行工具调用（委托给 ToolRegistry）
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            
        Returns:
            格式化后的工具执行结果字符串
        """
        if not self.tool_registry:
            return f"Error: 工具 '{tool_name}' 不可用，ToolRegistry 未注入"
        
        logger.info(
            "intent_analyzer_tool_call",
            tool_name=tool_name,
            arguments=tool_args,
        )
        
        result = await self.tool_registry.execute_tool(
            name=tool_name,
            arguments=tool_args,
            pre_allocated_tavily_key=self._tavily_key,
        )
        
        # 格式化 web_search 结果为可读文本
        if tool_name == "web_search" and hasattr(result, "results"):
            formatted = []
            for idx, res in enumerate(result.results[:5], 1):
                formatted.append(
                    f"{idx}. {res['title']}\n"
                    f"   URL: {res['url']}\n"
                    f"   摘要: {res['snippet']}\n"
                )
            return "\n".join(formatted) if formatted else "未找到相关搜索结果"
        
        if isinstance(result, str):
            return result
        
        return json.dumps(
            result.model_dump() if hasattr(result, "model_dump") else result,
            ensure_ascii=False,
        )
    
    async def execute(self, input_data: UserRequest) -> IntentAnalysisOutput:
        """
        分析用户学习需求
        
        若注入了 ToolRegistry，则执行增强流程：
        - Phase 1：ReAct 循环，按需调用 web_search 获取最新技术信息（最多 3 次迭代）
        - 优先将 Phase 1 的最终结果按 JSON 直出进行本地校验
        - 仅当本地校验失败时，才回退到 Phase 2 结构化提取 IntentAnalysisOutput
        
        否则，直接使用单阶段结构化输出（向后兼容）
        
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
        
        # 准备工具定义（决定使用哪种模式）
        tools = self._get_tools_definition()
        use_tools = bool(tools)
        
        # 构建工具简述列表（用于注入 System Prompt 模板）
        tools_for_prompt = [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
            }
            for t in tools
        ] if use_tools else None
        
        # 加载 System Prompt
        logger.debug("intent_analysis_loading_prompt", template="intent_analyzer.j2", use_tools=use_tools)
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
            tools=tools_for_prompt,
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
            use_tools=use_tools,
        )
        
        if use_tools:
            # ====== Phase 1: ReAct 循环（含 web_search 工具调用）======
            logger.info(
                "intent_analysis_phase1_react_started",
                user_id=user_request.user_id,
                tools_count=len(tools),
            )
            
            react_response = await self._call_llm(
                messages=messages,
                tools=tools,
                use_react=True,
                max_iterations=3,
            )
            
            phase1_text = react_response.choices[0].message.content or ""
            
            logger.info(
                "intent_analysis_phase1_react_completed",
                user_id=user_request.user_id,
                output_length=len(phase1_text),
            )

            # 优先尝试“一阶段直出 + 本地校验”，避免 Gemini 在二次 parse 时被截断。
            try:
                result = self._parse_phase1_structured_output(phase1_text)
                logger.info(
                    "intent_analysis_phase1_direct_parse_completed",
                    user_id=user_request.user_id,
                )
            except (ValueError, ValidationError) as parse_error:
                logger.warning(
                    "intent_analysis_phase1_direct_parse_failed",
                    user_id=user_request.user_id,
                    error=str(parse_error),
                    error_type=type(parse_error).__name__,
                )

                # ====== Phase 2: 从 Phase 1 文本中提取结构化数据 ======
                logger.info(
                    "intent_analysis_phase2_extraction_started",
                    user_id=user_request.user_id,
                )

                extraction_messages = [
                    {"role": "system", "content": self.EXTRACTION_SYSTEM_PROMPT},
                    {"role": "user", "content": phase1_text},
                ]

                result = await self._call_llm(
                    messages=extraction_messages,
                    response_model=IntentAnalysisOutput,
                )

                logger.info(
                    "intent_analysis_phase2_extraction_completed",
                    user_id=user_request.user_id,
                )
        else:
            # ====== 无工具模式：单阶段结构化输出（向后兼容）======
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
        
        # 强制以用户显式指定的语言偏好为准，禁止 LLM 覆盖
        # 原因：primary_language / secondary_language 是用户主观设置，LLM 可能根据目标文本语言
        # 自行推断（如目标写成英文就推断为 en），导致与用户真实设定不符
        result.language_preferences = language_prefs
        
        # 修正 full_analysis_data 中的 language 指令字段，与强制语言偏好保持一致
        if result.full_analysis_data:
            if language_prefs.primary_language == "zh":
                result.full_analysis_data["language"] = "请使用简体中文生成所有内容"
            elif language_prefs.primary_language == "en":
                result.full_analysis_data["language"] = "Please generate all content in English"
            else:
                result.full_analysis_data["language"] = f"Please generate all content in {language_prefs.primary_language}"
        
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
