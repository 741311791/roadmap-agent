"""
REGENERATE 快速全量重建编辑器单元测试。
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.agents.roadmap_regenerate_editor import (
    FastFullRegenerateEditorAgent,
    PlannedStage,
    RoadmapRegenerateOutline,
)
from app.models.domain import (
    EditPlan,
    LearningPreferences,
    RoadmapEditInput,
    RoadmapFramework,
    SimplifiedConcept,
    SimplifiedModule,
    SimplifiedStage,
    StageEditTask,
)


def create_preferences() -> LearningPreferences:
    """创建测试偏好。"""
    return LearningPreferences(
        learning_goal="转向后端开发方向",
        available_hours_per_week=10,
        motivation="转岗",
        current_level="intermediate",
        career_background="有 Python 基础，希望补齐工程化能力",
        content_preference=["text", "hands_on"],
        primary_language="zh",
    )


def create_framework() -> RoadmapFramework:
    """创建测试路线图。"""
    from app.models.domain import Concept, Module, Stage

    return RoadmapFramework(
        roadmap_id="roadmap-regenerate-test",
        title="旧路线图",
        total_estimated_hours=20.0,
        recommended_completion_weeks=2,
        stages=[
            Stage(
                stage_id="stage-1",
                name="旧阶段1",
                description="旧描述1",
                order=1,
                modules=[
                    Module(
                        module_id="module-1",
                        name="旧模块1",
                        description="旧模块描述1",
                        concepts=[
                            Concept(
                                concept_id="concept-1",
                                name="旧概念1",
                                description="旧概念描述1",
                                estimated_hours=4.0,
                                difficulty="easy",
                                keywords=["python"],
                                prerequisites=[],
                            )
                        ],
                    )
                ],
            )
        ],
    )


@pytest.mark.asyncio
async def test_fast_regenerate_editor_execute():
    """快路径全量重建应返回合法输出。"""
    agent = FastFullRegenerateEditorAgent()

    outline = RoadmapRegenerateOutline(
        roadmap_id="roadmap-regenerate-test",
        title="新路线图",
        total_estimated_hours=30.0,
        recommended_completion_weeks=3,
        stages=[
            PlannedStage(
                stage_id="stage-1",
                name="基础阶段",
                description="重建后的基础阶段",
                order=1,
                estimated_hours=15.0,
                focus_areas=["python", "api", "sql"],
            ),
            PlannedStage(
                stage_id="stage-2",
                name="进阶阶段",
                description="重建后的进阶阶段",
                order=2,
                estimated_hours=15.0,
                focus_areas=["deployment", "docker", "testing"],
            ),
        ],
    )
    stage1 = SimplifiedStage(
        stage_id="stage-1",
        name="基础阶段",
        description="重建后的基础阶段",
        order=1,
        modules=[
            SimplifiedModule(
                module_id="mod-1-1",
                name="后端基础",
                description="理解 API 与数据库基础",
                concepts=[
                    SimplifiedConcept(
                        concept_id="c-1-1-1",
                        name="HTTP 基础",
                        description="理解请求响应模型",
                        estimated_hours=5.0,
                        prerequisites=[],
                        difficulty="easy",
                        keywords=["http", "request", "response"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-1-1-2",
                        name="SQL 基础",
                        description="学习基础查询",
                        estimated_hours=5.0,
                        prerequisites=["c-1-1-1"],
                        difficulty="medium",
                        keywords=["sql", "query", "database"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-1-1-3",
                        name="FastAPI 路由",
                        description="定义接口路由",
                        estimated_hours=5.0,
                        prerequisites=["c-1-1-1"],
                        difficulty="medium",
                        keywords=["fastapi", "routing", "api"],
                    ),
                ],
            )
        ],
    )
    stage2 = SimplifiedStage(
        stage_id="stage-2",
        name="进阶阶段",
        description="重建后的进阶阶段",
        order=2,
        modules=[
            SimplifiedModule(
                module_id="mod-2-1",
                name="工程实践",
                description="部署、测试与监控",
                concepts=[
                    SimplifiedConcept(
                        concept_id="c-2-1-1",
                        name="Docker 部署",
                        description="容器化打包与部署",
                        estimated_hours=5.0,
                        prerequisites=["c-1-1-3"],
                        difficulty="medium",
                        keywords=["docker", "deployment", "container"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-2-1-2",
                        name="自动化测试",
                        description="接口与单元测试",
                        estimated_hours=5.0,
                        prerequisites=["c-1-1-3"],
                        difficulty="medium",
                        keywords=["pytest", "testing", "qa"],
                    ),
                    SimplifiedConcept(
                        concept_id="c-2-1-3",
                        name="上线项目实战",
                        description="完成完整的小型后端项目",
                        estimated_hours=5.0,
                        prerequisites=["c-2-1-1", "c-2-1-2"],
                        difficulty="hard",
                        keywords=["project", "deployment", "backend"],
                    ),
                ],
            )
        ],
    )

    agent._plan_outline = AsyncMock(return_value=outline)
    agent._generate_stage = AsyncMock(side_effect=[stage1, stage2])
    helper = CurriculumArchitectAgent(agent_id="helper")
    agent._postprocess_helper = helper

    input_data = RoadmapEditInput(
        existing_framework=create_framework(),
        user_preferences=create_preferences(),
        edit_plan=EditPlan(
            feedback_summary="整体改为后端开发路线图",
            tasks=[
                StageEditTask(
                    action="REGENERATE",
                    stage_id=None,
                    instruction="根据新的后端目标重新设计路线图。",
                )
            ],
        ),
    )

    result = await agent.execute(input_data)

    assert result.framework.roadmap_id == "roadmap-regenerate-test"
    assert len(result.framework.stages) == 2
    assert result.framework.total_estimated_hours == 30.0
    assert result.framework.recommended_completion_weeks == 3
    assert result.modified_node_ids
    assert "REGENERATE" in result.modification_summary
