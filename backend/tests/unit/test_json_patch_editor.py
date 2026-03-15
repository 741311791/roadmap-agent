"""
JSON Patch 编辑器单元测试。
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.agents.json_patch_editor import (
    AdaptiveRoadmapEditorAgent,
    JsonPatchEditorAgent,
    JsonPatchResponse,
)
from app.models.domain import (
    Concept,
    EditPlan,
    LearningPreferences,
    Module,
    RoadmapEditInput,
    RoadmapFramework,
    RoadmapEditOutput,
    Stage,
    StageEditTask,
)


def create_preferences() -> LearningPreferences:
    """创建测试偏好。"""
    return LearningPreferences(
        learning_goal="提升全栈开发能力",
        available_hours_per_week=8,
        motivation="转岗",
        current_level="intermediate",
        career_background="后端工程经验 2 年",
        content_preference=["text", "hands_on"],
        primary_language="zh",
    )


def create_framework() -> RoadmapFramework:
    """创建测试路线图。"""
    return RoadmapFramework(
        roadmap_id="test-roadmap",
        title="测试路线图",
        total_estimated_hours=15.0,
        recommended_completion_weeks=2,
        stages=[
            Stage(
                stage_id="stage-1",
                name="基础阶段",
                description="基础知识",
                order=1,
                modules=[
                    Module(
                        module_id="module-1",
                        name="基础模块",
                        description="基础模块描述",
                        concepts=[
                            Concept(
                                concept_id="concept-1",
                                name="原始概念",
                                description="原始描述",
                                estimated_hours=3.0,
                                difficulty="easy",
                                keywords=["python"],
                                prerequisites=[],
                                content_status="completed",
                                tutorial_id="tutorial-1",
                                content_ref="s3://bucket/tutorial-1.md",
                                resources_status="completed",
                                resources_id="resource-1",
                                resources_count=2,
                                quiz_status="completed",
                                quiz_id="quiz-1",
                                quiz_questions_count=4,
                            )
                        ],
                    )
                ],
            ),
            Stage(
                stage_id="stage-2",
                name="进阶阶段",
                description="进阶知识",
                order=2,
                modules=[
                    Module(
                        module_id="module-2",
                        name="进阶模块",
                        description="进阶模块描述",
                        concepts=[
                            Concept(
                                concept_id="concept-2",
                                name="高级概念",
                                description="高级描述",
                                estimated_hours=12.0,
                                difficulty="hard",
                                keywords=["fastapi"],
                                prerequisites=["concept-1"],
                            )
                        ],
                    )
                ],
            ),
        ],
    )


class TestJsonPatchEditorAgent:
    """测试 JSON Patch 编辑器。"""

    @pytest.mark.asyncio
    async def test_execute_replace_concept_preserves_operational_fields(self):
        """替换概念字段时应保留运营字段。"""
        agent = JsonPatchEditorAgent()
        agent._load_user_constraints = AsyncMock(return_value={})
        agent._generate_patch_response = AsyncMock(
            return_value=JsonPatchResponse.model_validate(
                {
                    "patches": [
                        {
                            "op": "replace",
                            "path": "/stages/0/modules/0/concepts/0/name",
                            "value": "更新后的概念名称",
                        },
                        {
                            "op": "replace",
                            "path": "/stages/0/modules/0/concepts/0/description",
                            "value": "更新后的概念描述",
                        },
                        {
                            "op": "replace",
                            "path": "/stages/0/modules/0/concepts/0/estimated_hours",
                            "value": 4.0,
                        },
                    ]
                }
            )
        )

        input_data = RoadmapEditInput(
            existing_framework=create_framework(),
            user_preferences=create_preferences(),
            edit_plan=EditPlan(
                feedback_summary="更新概念描述",
                tasks=[
                    StageEditTask(
                        action="UPDATE",
                        stage_id="stage-1",
                        instruction="更新概念1的名称、描述和时长。",
                    )
                ],
            ),
        )

        result = await agent.execute(input_data)

        concept = result.framework.stages[0].modules[0].concepts[0]
        assert concept.name == "更新后的概念名称"
        assert concept.description == "更新后的概念描述"
        assert concept.estimated_hours == 4.0
        assert concept.tutorial_id == "tutorial-1"
        assert concept.content_ref == "s3://bucket/tutorial-1.md"
        assert "concept-1" in result.modified_node_ids
        assert result.framework.total_estimated_hours == 16.0

    @pytest.mark.asyncio
    async def test_execute_add_stage_recomputes_order_and_weeks(self):
        """新增 Stage 后应重排 order 并重算周数。"""
        agent = JsonPatchEditorAgent()
        agent._load_user_constraints = AsyncMock(return_value={})
        agent._generate_patch_response = AsyncMock(
            return_value=JsonPatchResponse.model_validate(
                {
                    "patches": [
                        {
                            "op": "add",
                            "path": "/stages/1",
                            "value": {
                                "index": 1,
                                "stage_id": "stage-new",
                                "name": "数据库基础",
                                "description": "新增数据库阶段",
                                "modules": [
                                    {
                                        "index": 0,
                                        "module_id": "module-new",
                                        "name": "SQL 入门",
                                        "description": "学习 SQL 基础",
                                        "concepts": [
                                            {
                                                "index": 0,
                                                "concept_id": "concept-new",
                                                "name": "SQL 查询基础",
                                                "description": "掌握基础查询。",
                                                "estimated_hours": 5.0,
                                                "difficulty": "medium",
                                                "prerequisites": ["concept-1"],
                                                "keywords": ["sql"],
                                            }
                                        ],
                                    }
                                ],
                            },
                        }
                    ]
                }
            )
        )

        input_data = RoadmapEditInput(
            existing_framework=create_framework(),
            user_preferences=create_preferences(),
            edit_plan=EditPlan(
                feedback_summary="新增数据库基础阶段",
                tasks=[
                    StageEditTask(
                        action="CREATE",
                        stage_id=None,
                        instruction="在第一阶段后新增数据库基础阶段。",
                    )
                ],
            ),
        )

        result = await agent.execute(input_data)

        assert [stage.order for stage in result.framework.stages] == [1, 2, 3]
        assert result.framework.stages[1].stage_id == "stage-new"
        assert result.framework.total_estimated_hours == 20.0
        assert result.framework.recommended_completion_weeks == 3
        assert "concept-new" in result.modified_node_ids

    @pytest.mark.asyncio
    async def test_execute_ignores_index_patch_operations(self):
        """模型误输出 /index 路径时应忽略而不是失败。"""
        agent = JsonPatchEditorAgent()
        agent._load_user_constraints = AsyncMock(return_value={})
        agent._generate_patch_response = AsyncMock(
            return_value=JsonPatchResponse.model_validate(
                {
                    "patches": [
                        {
                            "op": "replace",
                            "path": "/stages/1/index",
                            "value": 2,
                        },
                        {
                            "op": "replace",
                            "path": "/stages/1/modules/0/concepts/0/name",
                            "value": "精简后的高级概念",
                        },
                    ]
                }
            )
        )

        input_data = RoadmapEditInput(
            existing_framework=create_framework(),
            user_preferences=create_preferences(),
            edit_plan=EditPlan(
                feedback_summary="精简第二阶段",
                tasks=[
                    StageEditTask(
                        action="UPDATE",
                        stage_id="stage-2",
                        instruction="精简第二阶段概念命名。",
                    )
                ],
            ),
        )

        result = await agent.execute(input_data)

        assert (
            result.framework.stages[1].modules[0].concepts[0].name
            == "精简后的高级概念"
        )

    @pytest.mark.asyncio
    async def test_execute_rejects_disallowed_path(self):
        """非法路径应直接失败。"""
        agent = JsonPatchEditorAgent()
        agent._load_user_constraints = AsyncMock(return_value={})
        agent._generate_patch_response = AsyncMock(
            return_value=JsonPatchResponse.model_validate(
                {
                    "patches": [
                        {
                            "op": "replace",
                            "path": "/title",
                            "value": "非法修改标题",
                        }
                    ]
                }
            )
        )

        input_data = RoadmapEditInput(
            existing_framework=create_framework(),
            user_preferences=create_preferences(),
            edit_plan=EditPlan(
                feedback_summary="尝试非法修改标题",
                tasks=[
                    StageEditTask(
                        action="UPDATE",
                        stage_id="stage-1",
                        instruction="修改标题。",
                    )
                ],
            ),
        )

        with pytest.raises(ValueError, match="不允许修改该路径"):
            await agent.execute(input_data)


class TestAdaptiveRoadmapEditorAgent:
    """测试路线图编辑适配层。"""

    @pytest.mark.asyncio
    async def test_fallback_to_legacy_editor_when_patch_fails(self):
        """patch 失败时应回退到传统编辑器。"""
        patch_editor = AsyncMock()
        patch_editor.execute.side_effect = ValueError("patch failed")
        legacy_output = RoadmapEditOutput(
            framework=create_framework(),
            modification_summary="fallback summary",
            modified_node_ids=["concept-1"],
        )
        legacy_editor = AsyncMock()
        legacy_editor.execute.return_value = legacy_output
        agent = AdaptiveRoadmapEditorAgent(
            patch_editor=patch_editor,
            regenerate_editor=AsyncMock(),
            legacy_editor=legacy_editor,
        )

        input_data = RoadmapEditInput(
            existing_framework=create_framework(),
            user_preferences=create_preferences(),
            edit_plan=EditPlan(
                feedback_summary="更新阶段",
                tasks=[
                    StageEditTask(
                        action="UPDATE",
                        stage_id="stage-1",
                        instruction="更新阶段内容。",
                    )
                ],
            ),
        )

        result = await agent.execute(input_data)

        patch_editor.execute.assert_called_once()
        legacy_editor.execute.assert_called_once()
        assert result.modification_summary == "fallback summary"

    @pytest.mark.asyncio
    async def test_route_regenerate_directly_to_legacy_editor(self):
        """REGENERATE 应直接走快速全量重建编辑器。"""
        patch_editor = AsyncMock()
        regenerate_editor = AsyncMock()
        regenerate_output = RoadmapEditOutput(
            framework=create_framework(),
            modification_summary="regenerate summary",
            modified_node_ids=["concept-2"],
        )
        regenerate_editor.execute.return_value = regenerate_output
        legacy_output = RoadmapEditOutput(
            framework=create_framework(),
            modification_summary="legacy regenerate summary",
            modified_node_ids=[],
        )
        legacy_editor = AsyncMock()
        legacy_editor.execute.return_value = legacy_output
        agent = AdaptiveRoadmapEditorAgent(
            patch_editor=patch_editor,
            regenerate_editor=regenerate_editor,
            legacy_editor=legacy_editor,
        )

        input_data = RoadmapEditInput(
            existing_framework=create_framework(),
            user_preferences=create_preferences(),
            edit_plan=EditPlan(
                feedback_summary="整体重建",
                tasks=[
                    StageEditTask(
                        action="REGENERATE",
                        stage_id=None,
                        instruction="根据新的学习目标重建路线图。",
                    )
                ],
            ),
        )

        result = await agent.execute(input_data)

        patch_editor.execute.assert_not_called()
        regenerate_editor.execute.assert_called_once()
        legacy_editor.execute.assert_not_called()
        assert result.modification_summary == "regenerate summary"
