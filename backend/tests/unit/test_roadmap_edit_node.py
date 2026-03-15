"""
roadmap_edit_node 单元测试。
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.orchestrator.nodes.roadmap_edit import roadmap_edit_node
from app.models.domain import (
    Concept,
    EditPlan,
    EditPlanAnalyzerOutput,
    LearningPreferences,
    Module,
    RoadmapEditOutput,
    RoadmapFramework,
    Stage,
    StageEditTask,
    UserRequest,
)


def create_preferences() -> LearningPreferences:
    """创建测试偏好。"""
    return LearningPreferences(
        learning_goal="提升 Web 开发能力",
        available_hours_per_week=8,
        motivation="转岗",
        current_level="intermediate",
        career_background="Python 开发经验 2 年",
        content_preference=["text"],
        primary_language="zh",
    )


def create_framework(name: str = "原始概念") -> RoadmapFramework:
    """创建测试路线图。"""
    return RoadmapFramework(
        roadmap_id="roadmap-node-test",
        title="测试路线图",
        total_estimated_hours=6.0,
        recommended_completion_weeks=1,
        stages=[
            Stage(
                stage_id="stage-1",
                name="基础阶段",
                description="基础阶段描述",
                order=1,
                modules=[
                    Module(
                        module_id="module-1",
                        name="基础模块",
                        description="基础模块描述",
                        concepts=[
                            Concept(
                                concept_id="concept-1",
                                name=name,
                                description="概念描述",
                                estimated_hours=6.0,
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
async def test_roadmap_edit_node_returns_expected_state():
    """节点应返回 handler 所需字段，并保留 editor_agent 信息。"""
    runtime_context = MagicMock()
    mock_agent = AsyncMock()
    mock_agent.agent_id = "adaptive_roadmap_editor"
    mock_agent.execute.return_value = RoadmapEditOutput(
        framework=create_framework(name="更新后的概念"),
        modification_summary="已更新概念",
        modified_node_ids=["concept-1"],
    )
    runtime_context.agent_factory.create_roadmap_editor.return_value = mock_agent

    preferences = create_preferences()
    state = {
        "task_id": "task-1",
        "roadmap_id": "roadmap-node-test",
        "roadmap_framework": create_framework(),
        "edit_plan": EditPlanAnalyzerOutput(
            edit_plan=EditPlan(
                feedback_summary="更新第一阶段",
                tasks=[
                    StageEditTask(
                        action="UPDATE",
                        stage_id="stage-1",
                        instruction="更新概念名称。",
                    )
                ],
            ),
            confidence=0.92,
        ),
        "modification_count": 1,
        "edit_source": "human_review",
        "user_request": UserRequest(
            user_id="user-1",
            session_id="session-1",
            preferences=preferences,
        ),
    }
    config = {
        "configurable": {
            "runtime_context": runtime_context,
        }
    }

    with patch(
        "app.core.orchestrator.nodes.roadmap_edit.execution_logger.info",
        new_callable=AsyncMock,
    ) as mock_log:
        result = await roadmap_edit_node(state, config)

    assert result["current_step"] == "roadmap_edit"
    assert result["roadmap_id"] == "roadmap-node-test"
    assert result["edit_source"] == "human_review"
    assert result["modified_node_ids"] == ["concept-1"]
    assert result["modified_framework"].stages[0].modules[0].concepts[0].name == "更新后的概念"
    mock_agent.execute.assert_called_once()
    mock_log.assert_called_once()
    assert mock_log.await_args.kwargs["agent_name"] == "adaptive_roadmap_editor"
