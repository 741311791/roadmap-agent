"""
REGENERATE 专用的快速全量重建编辑器。

设计目标：
1. 仅服务于 EditPlan 中包含 REGENERATE 的场景。
2. 借鉴 CurriculumArchitectAgent 的 Plan-and-Execute 思路：
   - 先生成 Stage 级大纲
   - 再并行生成各 Stage 的 Module/Concept
   - 最后本地合并、补全默认字段、修复依赖
3. 不修改 CurriculumArchitectAgent 本体，只复用其后处理能力。
"""
from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any

import structlog
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.agents.framework_diff import compute_modified_node_ids
from app.agents.framework_normalizer import normalize_framework_ids
from app.config.settings import settings
from app.models.domain import (
    ConstraintNames,
    EditPlan,
    LearningPreferences,
    RoadmapEditInput,
    RoadmapEditOutput,
    RoadmapFramework,
    SimplifiedRoadmapFramework,
    SimplifiedStage,
)

logger = structlog.get_logger()


class PlannedStage(BaseModel):
    """路线图规划阶段的 Stage 大纲。"""

    stage_id: str = Field(..., description="Stage ID，如 'stage-1'")
    name: str = Field(..., description="Stage 名称")
    description: str = Field(..., description="Stage 描述")
    order: int = Field(..., ge=1, description="Stage 顺序")
    estimated_hours: float = Field(..., ge=1.0, description="预计学习时长（小时）")
    focus_areas: list[str] = Field(..., min_length=1, description="核心学习重点关键词")


class RoadmapRegenerateOutline(BaseModel):
    """REGENERATE 阶段产出的路线图大纲。"""

    roadmap_id: str
    title: str
    total_estimated_hours: float
    recommended_completion_weeks: int
    stages: list[PlannedStage] = Field(..., min_length=1)


class FastFullRegenerateEditorAgent(BaseAgent):
    """
    REGENERATE 专用快速全量重建编辑器。

    使用 ARCHITECT 配置，让全量重建复用已经优化过的模型与调用策略。
    """

    def __init__(
        self,
        agent_id: str = "fast_full_regenerate_editor",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.ARCHITECT_PROVIDER,
            model_name=model_name or settings.ARCHITECT_MODEL,
            base_url=base_url or settings.ARCHITECT_BASE_URL,
            api_key=api_key or settings.ARCHITECT_API_KEY,
            temperature=0.1,
        )
        self._postprocess_helper = CurriculumArchitectAgent(
            agent_id=f"{agent_id}_helper",
            model_provider=model_provider or settings.ARCHITECT_PROVIDER,
            model_name=model_name or settings.ARCHITECT_MODEL,
            base_url=base_url or settings.ARCHITECT_BASE_URL,
            api_key=api_key or settings.ARCHITECT_API_KEY,
        )

    def _get_required_constraints(self) -> list[str]:
        """REGENERATE 编辑器需要的约束。"""
        return [
            ConstraintNames.LANGUAGE,
            ConstraintNames.USER_GOAL,
            ConstraintNames.USER_PROFILE,
            ConstraintNames.SKILL_GAP,
            ConstraintNames.RECOMMENDED_FOCUS,
        ]

    async def execute(self, input_data: RoadmapEditInput) -> RoadmapEditOutput:
        """
        执行 REGENERATE 快路径。

        Args:
            input_data: 路线图编辑输入。

        Returns:
            路线图编辑输出。
        """
        existing_framework = input_data.existing_framework
        user_preferences = input_data.user_preferences
        edit_plan = input_data.edit_plan
        user_constraints = await self._load_user_constraints(
            roadmap_id=existing_framework.roadmap_id
        )

        if not any(task.action == "REGENERATE" for task in edit_plan.tasks):
            raise ValueError("FastFullRegenerateEditorAgent 只支持 REGENERATE 场景。")

        prompt_context = self._prepare_prompt_context(
            input_data,
            user_constraints=user_constraints,
        )
        logger.info(
            "fast_regenerate_started",
            roadmap_id=existing_framework.roadmap_id,
            tasks_count=len(edit_plan.tasks),
        )

        outline = await self._plan_outline(prompt_context)
        stage_tasks = [
            self._generate_stage(planned_stage, outline, prompt_context)
            for planned_stage in outline.stages
        ]
        simplified_stages = list(await asyncio.gather(*stage_tasks))
        simplified_framework = SimplifiedRoadmapFramework(
            roadmap_id=outline.roadmap_id,
            title=outline.title,
            total_estimated_hours=outline.total_estimated_hours,
            recommended_completion_weeks=outline.recommended_completion_weeks,
            stages=sorted(simplified_stages, key=lambda stage: stage.order),
        )

        full_framework = self._postprocess_helper._convert_to_full_framework(
            simplified_framework
        )
        full_framework, fixes = self._postprocess_helper._check_and_fix_dependencies(
            full_framework
        )
        full_framework = normalize_framework_ids(full_framework)
        full_framework.roadmap_id = existing_framework.roadmap_id

        modified_node_ids = compute_modified_node_ids(
            old_framework=existing_framework,
            new_framework=full_framework,
        )
        modification_summary = self._build_summary(
            edit_plan=edit_plan,
            old_framework=existing_framework,
            new_framework=full_framework,
            modified_node_ids=modified_node_ids,
            fixes=fixes,
        )

        logger.info(
            "fast_regenerate_completed",
            roadmap_id=full_framework.roadmap_id,
            stages_count=len(full_framework.stages),
            modified_nodes_count=len(modified_node_ids),
            dependency_fixes=len(fixes),
        )
        return RoadmapEditOutput(
            framework=full_framework,
            modification_summary=modification_summary,
            modified_node_ids=modified_node_ids,
        )

    def _prepare_prompt_context(
        self,
        input_data: RoadmapEditInput,
        user_constraints: dict[str, str],
    ) -> dict[str, Any]:
        """准备 prompt 所需的最小上下文。"""
        framework = input_data.existing_framework
        preferences = input_data.user_preferences
        edit_plan = input_data.edit_plan
        key_technologies = self._extract_key_technologies(framework)

        return {
            "roadmap_id": framework.roadmap_id,
            "current_title": framework.title,
            "current_total_estimated_hours": framework.total_estimated_hours,
            "current_recommended_completion_weeks": framework.recommended_completion_weeks,
            "existing_roadmap_summary": self._build_existing_roadmap_summary(framework),
            "regenerate_request_summary": edit_plan.feedback_summary,
            "regenerate_tasks_text": self._build_tasks_text(edit_plan),
            "user_goal": preferences.learning_goal,
            "parsed_goal": edit_plan.feedback_summary,
            "key_technologies": key_technologies,
            "current_level": preferences.current_level,
            "available_hours_per_week": preferences.available_hours_per_week,
            "motivation": preferences.motivation,
            "career_background": preferences.career_background,
            "primary_language": preferences.get_language_preferences().primary_language,
            "secondary_language": preferences.get_language_preferences().secondary_language,
            "user_constraints": user_constraints,
        }

    async def _plan_outline(self, prompt_context: dict[str, Any]) -> RoadmapRegenerateOutline:
        """第一阶段：生成重建后路线图的大纲。"""
        system_prompt = self._load_system_prompt(
            "roadmap_regenerate_outline.j2",
            **prompt_context,
        )
        messages = [{"role": "system", "content": system_prompt}]
        try:
            outline = await self._call_llm(
                messages=messages,
                response_model=RoadmapRegenerateOutline,
                use_two_stage=False,
            )
        except Exception as exc:
            logger.warning(
                "fast_regenerate_outline_direct_parse_failed",
                roadmap_id=prompt_context["roadmap_id"],
                error=str(exc),
                fallback="two_stage_generation",
            )
            outline = await self._call_llm(
                messages=messages,
                response_model=RoadmapRegenerateOutline,
                use_two_stage=True,
            )

        outline.roadmap_id = prompt_context["roadmap_id"]
        if not outline.stages:
            raise ValueError("REGENERATE outline 返回空 stages。")
        return outline

    async def _generate_stage(
        self,
        planned_stage: PlannedStage,
        outline: RoadmapRegenerateOutline,
        prompt_context: dict[str, Any],
    ) -> SimplifiedStage:
        """第二阶段：并行生成单个 Stage 结构。"""
        stage_context = {
            "user_goal": prompt_context["user_goal"],
            "parsed_goal": prompt_context["parsed_goal"],
            "key_technologies": prompt_context["key_technologies"],
            "current_level": prompt_context["current_level"],
            "available_hours_per_week": prompt_context["available_hours_per_week"],
            "motivation": prompt_context["motivation"],
            "primary_language": prompt_context["primary_language"],
            "stage_id": planned_stage.stage_id,
            "stage_name": planned_stage.name,
            "stage_description": planned_stage.description,
            "current_stage_order": planned_stage.order,
            "total_stages": len(outline.stages),
            "stage_estimated_hours": planned_stage.estimated_hours,
            "focus_areas": planned_stage.focus_areas,
            "previous_stages_text": self._format_previous_stages_text(
                outline,
                planned_stage.order,
            ),
            "existing_roadmap_summary": prompt_context["existing_roadmap_summary"],
            "regenerate_request_summary": prompt_context["regenerate_request_summary"],
        }
        system_prompt = self._load_system_prompt(
            "roadmap_regenerate_stage.j2",
            **stage_context,
        )
        messages = [{"role": "system", "content": system_prompt}]

        try:
            stage = await self._call_llm(
                messages=messages,
                response_model=SimplifiedStage,
                use_two_stage=False,
            )
        except Exception as exc:
            logger.warning(
                "fast_regenerate_stage_direct_parse_failed",
                stage_id=planned_stage.stage_id,
                error=str(exc),
                fallback="two_stage_generation",
            )
            stage = await self._call_llm(
                messages=messages,
                response_model=SimplifiedStage,
                use_two_stage=True,
            )

        stage.stage_id = planned_stage.stage_id
        stage.order = planned_stage.order
        return stage

    def _format_previous_stages_text(
        self,
        outline: RoadmapRegenerateOutline,
        current_stage_order: int,
    ) -> str:
        """格式化前序阶段摘要。"""
        previous_stages = [
            stage
            for stage in outline.stages
            if stage.order < current_stage_order
        ]
        if not previous_stages:
            return "无前序 Stage。请仅在本 Stage 内建立 prerequisites。"

        lines = ["前序 Stage 摘要："]
        for stage in previous_stages:
            focus_text = "、".join(stage.focus_areas[:3]) if stage.focus_areas else "（无）"
            lines.extend(
                [
                    f"- Stage {stage.order}（{stage.stage_id}）：{stage.name}",
                    f"  重点：{focus_text}",
                ]
            )
        return "\n".join(lines)

    def _extract_key_technologies(self, framework: RoadmapFramework) -> list[str]:
        """从已有路线图提取高频技术关键词。"""
        counter: Counter[str] = Counter()
        for stage in framework.stages:
            counter.update(stage.name.split())
            for module in stage.modules:
                counter.update(module.name.split())
                for concept in module.concepts:
                    counter.update(concept.keywords)
        most_common = [item for item, _ in counter.most_common(8)]
        return most_common or ["software-engineering", "web-development"]

    def _build_existing_roadmap_summary(self, framework: RoadmapFramework) -> str:
        """构建已有路线图摘要。"""
        lines = [
            f"当前路线图标题：{framework.title}",
            f"总时长：{framework.total_estimated_hours} 小时",
            f"推荐完成周数：{framework.recommended_completion_weeks} 周",
            "当前 Stage 概览：",
        ]
        for stage in framework.stages:
            module_names = "、".join(module.name for module in stage.modules[:4])
            lines.append(
                f"- Stage {stage.order}（{stage.stage_id}）：{stage.name} | 模块：{module_names}"
            )
        return "\n".join(lines)

    def _build_tasks_text(self, edit_plan: EditPlan) -> str:
        """构建任务文本。"""
        return "\n".join(
            f"- [{task.action}] {task.stage_id or 'NEW'}: {task.instruction}"
            for task in edit_plan.tasks
        )

    def _build_summary(
        self,
        edit_plan: EditPlan,
        old_framework: RoadmapFramework,
        new_framework: RoadmapFramework,
        modified_node_ids: list[str],
        fixes: list[str],
    ) -> str:
        """生成本地摘要。"""
        task_summary = "；".join(
            f"{task.action} {task.stage_id or 'new'}"
            for task in edit_plan.tasks
        )
        hours_diff = new_framework.total_estimated_hours - old_framework.total_estimated_hours
        hours_sign = "+" if hours_diff >= 0 else ""
        feedback_summary = edit_plan.feedback_summary.rstrip("。.!！?")
        fix_suffix = f"，依赖修复 {len(fixes)} 处" if fixes else ""
        return (
            f"{feedback_summary}。"
            f"执行了 {len(edit_plan.tasks)} 个修改任务（{task_summary}），"
            f"修改了 {len(modified_node_ids)} 个节点，"
            f"总时长变化: {hours_sign}{hours_diff:.1f}h{fix_suffix}"
        )
