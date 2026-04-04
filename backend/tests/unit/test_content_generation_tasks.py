"""
内容生成任务辅助函数测试
"""

from app.models.domain import Concept, Module, RoadmapFramework, Stage
from app.tasks.content_generation_tasks import _select_initial_concepts_for_generation


def _build_framework() -> RoadmapFramework:
    """
    构造用于测试的简化路线图
    """
    first_concept = Concept(
        concept_id="c-1-1-1",
        name="第一个概念",
        description="首个可学习概念",
        estimated_hours=0.1,
        prerequisites=[],
        difficulty="easy",
        keywords=["基础", "入门", "起点"],
    )
    second_concept = Concept(
        concept_id="c-1-1-2",
        name="第二个概念",
        description="后续概念",
        estimated_hours=0.1,
        prerequisites=["c-1-1-1"],
        difficulty="medium",
        keywords=["进阶", "串联", "练习"],
    )
    third_concept = Concept(
        concept_id="c-2-1-1",
        name="第三个概念",
        description="第二阶段概念",
        estimated_hours=0.1,
        prerequisites=["c-1-1-2"],
        difficulty="hard",
        keywords=["实战", "整合", "输出"],
    )

    return RoadmapFramework(
        roadmap_id="roadmap-test",
        title="测试路线图",
        total_estimated_hours=8,
        recommended_completion_weeks=2,
        stages=[
            Stage(
                stage_id="stage-1",
                name="阶段一",
                description="起步阶段",
                order=1,
                modules=[
                    Module(
                        module_id="mod-1-1",
                        name="模块一",
                        description="第一模块",
                        concepts=[first_concept, second_concept],
                    )
                ],
            ),
            Stage(
                stage_id="stage-2",
                name="阶段二",
                description="进阶阶段",
                order=2,
                modules=[
                    Module(
                        module_id="mod-2-1",
                        name="模块二",
                        description="第二模块",
                        concepts=[third_concept],
                    )
                ],
            ),
        ],
    )


def test_select_initial_concepts_for_generation_only_returns_first_concept():
    """
    应该只选择首个 Stage 的首个 Module 的首个 Concept
    """
    framework = _build_framework()
    concepts = [
        concept
        for stage in framework.stages
        for module in stage.modules
        for concept in module.concepts
    ]

    selected = _select_initial_concepts_for_generation(
        framework=framework,
        concepts=concepts,
        task_id="task-test",
    )

    assert len(selected) == 1
    assert selected[0].concept_id == "c-1-1-1"


def test_select_initial_concepts_for_generation_handles_empty_framework():
    """
    空路线图时应安全返回空列表
    """
    framework = RoadmapFramework(
        roadmap_id="roadmap-empty",
        title="空路线图",
        total_estimated_hours=0,
        recommended_completion_weeks=1,
        stages=[],
    )

    selected = _select_initial_concepts_for_generation(
        framework=framework,
        concepts=[],
        task_id="task-empty",
    )

    assert selected == []
