"""
Edit Plan Analyzer Agent（修改计划分析器）

负责将用户的自然语言反馈解析为结构化的修改计划，
指导 RoadmapEditorAgent 精确执行用户意图。
"""
import json
from app.agents.base import BaseAgent
from app.models.domain import (
    EditPlanAnalyzerInput,
    EditPlanAnalyzerOutput,
    EditPlan,
    EditIntent,
    RoadmapFramework,
    LearningPreferences,
)
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class EditPlanAnalyzerAgent(BaseAgent):
    """
    修改计划分析器 Agent
    
    将用户的自然语言反馈解析为结构化的修改计划：
    - 识别修改类型（add/remove/modify/reorder/merge/split）
    - 定位修改目标（stage/module/concept）
    - 生成优先级排序的修改意图列表
    - 明确必须保留不变的元素
    
    配置从环境变量加载：
    - ANALYZER_PROVIDER: 模型提供商（默认: openai）
    - ANALYZER_MODEL: 模型名称（默认: gpt-4o-mini）
    - ANALYZER_BASE_URL: 自定义 API 端点（可选）
    - ANALYZER_API_KEY: API 密钥（必需）
    """
    
    def __init__(
        self,
        agent_id: str = "edit_plan_analyzer",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        # 复用 Analyzer 配置，因为这是轻量级的意图识别任务
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.ANALYZER_PROVIDER,
            model_name=model_name or settings.ANALYZER_MODEL,
            base_url=base_url or settings.ANALYZER_BASE_URL,
            api_key=api_key or settings.ANALYZER_API_KEY,
            temperature=0.2,  # 低温度确保解析的稳定性
            max_tokens=2048,
        )
    
    def _build_roadmap_structure_summary(self, framework: RoadmapFramework) -> str:
        """
        构建路线图结构摘要，用于帮助 LLM 定位修改目标
        
        Args:
            framework: 路线图框架
            
        Returns:
            结构化的路线图摘要字符串
        """
        lines = []
        lines.append(f"路线图: {framework.title}")
        lines.append(f"总时长: {framework.total_estimated_hours} 小时")
        lines.append(f"阶段数: {len(framework.stages)}")
        lines.append("")
        
        for stage in framework.stages:
            lines.append(f"Stage {stage.order}: {stage.name} (ID: {stage.stage_id})")
            for module in stage.modules:
                lines.append(f"  └─ Module: {module.name} (ID: {module.module_id})")
                for concept in module.concepts:
                    difficulty_emoji = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}.get(concept.difficulty, "⚪")
                    lines.append(f"      └─ {difficulty_emoji} {concept.name} (ID: {concept.concept_id}, {concept.estimated_hours}h)")
        
        return "\n".join(lines)
    
    async def analyze(
        self,
        user_feedback: str,
        existing_framework: RoadmapFramework,
        user_preferences: LearningPreferences,
    ) -> EditPlanAnalyzerOutput:
        """
        分析用户反馈并生成结构化修改计划
        
        Args:
            user_feedback: 用户的原始反馈文本
            existing_framework: 当前路线图框架
            user_preferences: 用户偏好
            
        Returns:
            结构化的修改计划
        """
        logger.info(
            "edit_plan_analysis_started",
            feedback_preview=user_feedback[:100] + "..." if len(user_feedback) > 100 else user_feedback,
            roadmap_id=existing_framework.roadmap_id,
        )
        
        # 构建路线图结构摘要
        roadmap_summary = self._build_roadmap_structure_summary(existing_framework)
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "edit_plan_analyzer.j2",
            agent_name="Edit Plan Analyzer",
            role_description="分析用户的修改反馈，将其解析为结构化的修改计划，明确修改目标和保留要求。",
            roadmap_summary=roadmap_summary,
            user_goal=user_preferences.learning_goal,
            current_level=user_preferences.current_level,
        )
        
        # 构建用户消息
        user_message = f"""
请分析以下用户反馈，生成结构化的修改计划：

**用户反馈**:
{user_feedback}

**当前路线图结构**:
```
{roadmap_summary}
```

**用户背景**:
- 学习目标: {user_preferences.learning_goal}
- 当前水平: {user_preferences.current_level}
- 每周可投入时间: {user_preferences.available_hours_per_week} 小时

请严格以 JSON 格式返回修改计划。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 调用 LLM
        response = await self._call_llm(
            messages,
            response_format={"type": "json_object"},  # 强制 JSON 输出
        )
        
        # 解析输出
        content = response.choices[0].message.content
        
        try:
            # 尝试提取 JSON（LLM可能返回带代码块的内容）
            json_content = content
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                if json_end > json_start:
                    json_content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                if json_end > json_start:
                    json_content = content[json_start:json_end].strip()
            
            # 如果提取后是空字符串，尝试直接解析
            if not json_content.strip():
                json_content = content
            
            result_dict = json.loads(json_content)
            
            # 构建 EditIntent 列表
            intents = []
            for intent_data in result_dict.get("intents", []):
                intent = EditIntent(
                    intent_type=intent_data.get("intent_type", "modify"),
                    target_type=intent_data.get("target_type", "concept"),
                    target_id=intent_data.get("target_id"),
                    target_path=intent_data.get("target_path", ""),
                    description=intent_data.get("description", ""),
                    priority=intent_data.get("priority", "must"),
                )
                intents.append(intent)
            
            # 构建 EditPlan
            edit_plan = EditPlan(
                feedback_summary=result_dict.get("feedback_summary", user_feedback[:200]),
                intents=intents,
                scope_analysis=result_dict.get("scope_analysis", ""),
                preservation_requirements=result_dict.get("preservation_requirements", []),
            )
            
            # 构建输出
            output = EditPlanAnalyzerOutput(
                edit_plan=edit_plan,
                confidence=result_dict.get("confidence", 0.8),
                needs_clarification=result_dict.get("needs_clarification", False),
                clarification_questions=result_dict.get("clarification_questions", []),
            )
            
            logger.info(
                "edit_plan_analysis_completed",
                roadmap_id=existing_framework.roadmap_id,
                intents_count=len(intents),
                confidence=output.confidence,
                needs_clarification=output.needs_clarification,
            )
            
            return output
            
        except json.JSONDecodeError as e:
            logger.error(
                "edit_plan_analysis_json_parse_error",
                error=str(e),
                content_preview=content[:500],
                raw_content=content,  # 记录完整原始内容用于调试
                json_content_tried=json_content[:200] if 'json_content' in locals() else None,
            )
            # 返回默认的修改计划
            return EditPlanAnalyzerOutput(
                edit_plan=EditPlan(
                    feedback_summary=user_feedback[:200],
                    intents=[
                        EditIntent(
                            intent_type="modify",
                            target_type="stage",
                            target_id=None,
                            target_path="整个路线图",
                            description=user_feedback,
                            priority="must",
                        )
                    ],
                    scope_analysis="解析失败，将用户反馈作为整体修改意图",
                    preservation_requirements=[],
                ),
                confidence=0.3,
                needs_clarification=True,
                clarification_questions=["请您更具体地说明想要修改的内容？"],
            )
    
    async def execute(self, input_data: EditPlanAnalyzerInput) -> EditPlanAnalyzerOutput:
        """实现基类的抽象方法"""
        return await self.analyze(
            user_feedback=input_data.user_feedback,
            existing_framework=input_data.existing_framework,
            user_preferences=input_data.user_preferences,
        )

