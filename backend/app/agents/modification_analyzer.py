"""
Modification Analyzer Agent（修改意图分析师）

分析用户自然语言修改意见，识别修改目标和具体要求。
支持多目标识别，可以从一条消息中提取多个修改意图。
"""
import json
from typing import Optional, Dict, Any
from app.agents.base import BaseAgent
from app.models.domain import (
    RoadmapFramework,
    ModificationAnalysisOutput,
    SingleModificationIntent,
    ModificationType,
)
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class ModificationAnalyzerAgent(BaseAgent):
    """
    修改意图分析师 Agent
    
    配置从环境变量加载：
    - MODIFICATION_ANALYZER_PROVIDER: 模型提供商（默认: openai）
    - MODIFICATION_ANALYZER_MODEL: 模型名称（默认: gpt-4o-mini）
    - MODIFICATION_ANALYZER_BASE_URL: 自定义 API 端点（可选）
    - MODIFICATION_ANALYZER_API_KEY: API 密钥（默认复用 ANALYZER_API_KEY）
    """
    
    def __init__(
        self,
        agent_id: str = "modification_analyzer",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.MODIFICATION_ANALYZER_PROVIDER,
            model_name=model_name or settings.MODIFICATION_ANALYZER_MODEL,
            base_url=base_url or settings.MODIFICATION_ANALYZER_BASE_URL,
            api_key=api_key or settings.get_modification_analyzer_api_key,
            temperature=0.3,  # 低温度，确保分析准确
            max_tokens=2048,
        )
    
    async def analyze(
        self,
        user_message: str,
        roadmap_framework: RoadmapFramework,
        current_context: Optional[Dict[str, Any]] = None,
    ) -> ModificationAnalysisOutput:
        """
        分析用户修改意图
        
        Args:
            user_message: 用户的自然语言修改意见
            roadmap_framework: 当前路线图框架（用于匹配目标）
            current_context: 当前上下文（如用户正在查看的 concept_id）
            
        Returns:
            解析后的修改意图（支持多目标）
        """
        import time
        start_time = time.time()
        
        logger.info(
            "modification_analysis_started",
            agent="modification_analyzer",
            message_length=len(user_message),
            message_preview=user_message[:100],
            roadmap_id=roadmap_framework.roadmap_id,
            roadmap_title=roadmap_framework.title,
            has_context=current_context is not None,
            context_concept_id=current_context.get("concept_id") if current_context else None,
        )
        
        # 构建路线图结构摘要，供 LLM 匹配目标
        logger.debug(
            "modification_analysis_building_summary",
            agent="modification_analyzer",
            stages_count=len(roadmap_framework.stages),
        )
        roadmap_summary = self._build_roadmap_summary(roadmap_framework)
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "modification_analyzer.j2",
            agent_name="Modification Analyzer",
            role_description="专业的修改意图分析师，擅长从用户自然语言中提取修改目标和具体要求，支持多目标识别。",
            roadmap_summary=roadmap_summary,
            current_context=current_context,
        )
        
        logger.debug(
            "modification_analysis_prompt_loaded",
            agent="modification_analyzer",
            prompt_length=len(system_prompt),
        )
        
        # 构建用户消息
        context_info = ""
        if current_context:
            if current_context.get("concept_id"):
                context_info = f"\n当前用户正在查看的概念 ID: {current_context['concept_id']}"
            if current_context.get("concept_name"):
                context_info += f"\n概念名称: {current_context['concept_name']}"
        
        user_prompt = f"""
请分析以下用户修改意见，提取所有修改意图：

**用户消息**:
{user_message}
{context_info}

**要求**:
1. 识别所有修改目标（可能有多个）
2. 为每个目标提取具体修改要求
3. 将目标映射到路线图中的具体 concept
4. 如果无法明确目标，设置 needs_clarification = true
5. 输出 JSON 格式

请以 JSON 格式返回分析结果。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        # 调用 LLM
        logger.info(
            "modification_analysis_calling_llm",
            agent="modification_analyzer",
            model=self.model_name,
            provider=self.model_provider,
            messages_count=len(messages),
        )
        
        llm_start = time.time()
        response = await self._call_llm(messages)
        llm_duration = time.time() - llm_start
        
        # 解析输出
        content = response.choices[0].message.content
        logger.info(
            "modification_analysis_llm_completed",
            agent="modification_analyzer",
            response_length=len(content),
            llm_duration_seconds=llm_duration,
        )
        
        try:
            # 提取 JSON
            json_content = self._extract_json(content)
            result_dict = json.loads(json_content)
            
            # 构建 SingleModificationIntent 列表
            intents = []
            for intent_data in result_dict.get("intents", []):
                try:
                    # 转换 modification_type 字符串为枚举
                    mod_type_str = intent_data.get("modification_type", "tutorial")
                    mod_type = ModificationType(mod_type_str.lower())
                    
                    intent = SingleModificationIntent(
                        modification_type=mod_type,
                        target_id=intent_data.get("target_id", ""),
                        target_name=intent_data.get("target_name", ""),
                        specific_requirements=intent_data.get("specific_requirements", []),
                        priority=intent_data.get("priority", "medium"),
                    )
                    intents.append(intent)
                except Exception as e:
                    logger.warning(
                        "modification_intent_parse_failed",
                        error=str(e),
                        intent_data=intent_data,
                    )
            
            # 构建输出
            result = ModificationAnalysisOutput(
                intents=intents,
                overall_confidence=result_dict.get("overall_confidence", 0.8),
                needs_clarification=result_dict.get("needs_clarification", False),
                clarification_questions=result_dict.get("clarification_questions", []),
                analysis_reasoning=result_dict.get("analysis_reasoning", ""),
            )
            
            total_duration = time.time() - start_time
            
            # Log each detected intent for debugging
            for i, intent in enumerate(intents):
                logger.info(
                    "modification_analysis_intent_detected",
                    agent="modification_analyzer",
                    intent_idx=i + 1,
                    modification_type=intent.modification_type.value,
                    target_id=intent.target_id,
                    target_name=intent.target_name,
                    requirements_count=len(intent.specific_requirements),
                    priority=intent.priority,
                )
            
            logger.info(
                "modification_analysis_success",
                agent="modification_analyzer",
                intents_count=len(intents),
                needs_clarification=result.needs_clarification,
                overall_confidence=result.overall_confidence,
                total_duration_seconds=total_duration,
            )
            return result
            
        except json.JSONDecodeError as e:
            logger.error(
                "modification_analysis_json_parse_error",
                error=str(e),
                content=content[:500],
            )
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
        except Exception as e:
            logger.error(
                "modification_analysis_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise ValueError(f"修改意图分析失败: {e}")
    
    def _build_roadmap_summary(self, framework: RoadmapFramework) -> str:
        """
        构建路线图结构摘要
        
        生成包含所有 concept 的 ID 和名称的摘要，
        供 LLM 进行目标匹配。
        """
        lines = [f"路线图: {framework.title} (ID: {framework.roadmap_id})", ""]
        
        for stage in framework.stages:
            lines.append(f"阶段 {stage.order}: {stage.name} (ID: {stage.stage_id})")
            for module in stage.modules:
                lines.append(f"  模块: {module.name} (ID: {module.module_id})")
                for concept in module.concepts:
                    status_info = []
                    if concept.content_status == "completed":
                        status_info.append("有教程")
                    if concept.resources_status == "completed":
                        status_info.append(f"有资源({concept.resources_count})")
                    if concept.quiz_status == "completed":
                        status_info.append(f"有测验({concept.quiz_questions_count}题)")
                    
                    status_str = f" [{', '.join(status_info)}]" if status_info else ""
                    lines.append(
                        f"    概念: {concept.name} (ID: {concept.concept_id}){status_str}"
                    )
            lines.append("")
        
        return "\n".join(lines)
    
    def _extract_json(self, content: str) -> str:
        """从 LLM 响应中提取 JSON"""
        # 如果内容包含 ```json 代码块，提取其中的内容
        if "```json" in content:
            json_start = content.find("```json") + 7
            json_end = content.find("```", json_start)
            if json_end > json_start:
                return content[json_start:json_end].strip()
        elif "```" in content:
            json_start = content.find("```") + 3
            json_end = content.find("```", json_start)
            if json_end > json_start:
                return content[json_start:json_end].strip()
        
        # 尝试找到 JSON 对象
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return content[start:end]
        
        return content.strip()
    
    async def execute(self, input_data: Dict[str, Any]) -> ModificationAnalysisOutput:
        """实现基类的抽象方法"""
        return await self.analyze(
            user_message=input_data["user_message"],
            roadmap_framework=input_data["roadmap_framework"],
            current_context=input_data.get("current_context"),
        )

