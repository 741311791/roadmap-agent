"""
Edit Plan Analyzer Agent（修改计划分析器）

重构说明：
- 将修改指令收敛到 Stage 级别
- 输出 StageEditTask 列表（CREATE/UPDATE/REGENERATE）
- 利用 LLM 的语义理解能力，降低工程化复杂度
"""
from app.agents.base import BaseAgent
from app.models.domain import (
    EditPlanAnalyzerInput,
    EditPlanAnalyzerOutput,
    RoadmapFramework,
    LearningPreferences,
)
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class EditPlanAnalyzerAgent(BaseAgent):
    """
    修改计划分析器 Agent（简化版）
    
    重构后职责：
    - 将用户反馈解析为 Stage 级别的修改任务
    - 只生成 3 种动作：CREATE/UPDATE/REGENERATE
    - 用自然语言描述修改意图，而非细粒度指令
    
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
            max_tokens=2000,
        )
    
    def _get_required_constraints(self) -> list[str]:
        """编辑计划分析器需要的约束"""
        from app.models.domain import ConstraintNames
        return [
            # 通用约束
            ConstraintNames.LANGUAGE,
            ConstraintNames.USER_GOAL,
            ConstraintNames.USER_PROFILE,
            # 特定约束
            ConstraintNames.SKILL_GAP,
            ConstraintNames.PERSONALIZED_SUGGESTIONS,
        ]
    
    def _build_roadmap_structure_summary(self, framework: RoadmapFramework) -> str:
        """
        构建轻量结构摘要，用于帮助 LLM 定位修改目标
        
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
            lines.append(
                f"Stage {stage.order}: {stage.name} (ID: {stage.stage_id}, 模块数: {len(stage.modules)}, 时长: {stage.total_hours}h)"
            )
            for module in stage.modules:
                concept_preview = ", ".join(
                    f"{concept.name}({concept.concept_id})"
                    for concept in module.concepts[:3]
                )
                extra_count = len(module.concepts) - 3
                if extra_count > 0:
                    concept_preview += f", ... 其余 {extra_count} 个概念"
                lines.append(
                    f"  - Module: {module.name} (ID: {module.module_id}) | 概念: {concept_preview}"
                )
        
        return "\n".join(lines)
    
    async def execute(self, input_data: EditPlanAnalyzerInput) -> EditPlanAnalyzerOutput:
        """
        分析用户反馈并生成结构化修改计划
        
        Args:
            input_data: 包含用户反馈、现有框架和用户偏好
            
        Returns:
            结构化的修改计划
        """
        user_feedback = input_data.user_feedback
        existing_framework = input_data.existing_framework
        user_preferences = input_data.user_preferences
        
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
        
        # 使用 instructor 调用 LLM,自动验证和重试
        logger.info(
            "edit_plan_analysis_calling_llm",
            model=self.model_name,
            roadmap_id=existing_framework.roadmap_id,
        )
        
        result = await self._call_llm(
            messages,
            response_model=EditPlanAnalyzerOutput
        )
        
        logger.info(
            "edit_plan_analysis_completed",
            roadmap_id=existing_framework.roadmap_id,
            tasks_count=len(result.edit_plan.tasks),
            confidence=result.confidence,
        )
        
        return result
