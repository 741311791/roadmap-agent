"""
测试框架ID规范化工具

验证normalize_framework_ids函数是否正确：
1. 规范化Stage、Module、Concept的ID
2. 移除非标准ID（如xxx-new）
3. 更新prerequisites引用
"""
import pytest
from app.agents.framework_normalizer import normalize_framework_ids
from app.models.domain import RoadmapFramework, Stage, Module, Concept


def test_normalize_framework_ids_basic():
    """测试基本的ID规范化功能"""
    # 创建一个包含非标准ID的框架
    framework = RoadmapFramework(
        roadmap_id="test-roadmap-123",
        title="测试路线图",
        stages=[
            Stage(
                stage_id="s-1-old",  # 非标准ID
                name="阶段1",
                description="第一阶段",
                order=1,
                modules=[
                    Module(
                        module_id="m-1-1-old",  # 非标准ID
                        name="模块1",
                        description="第一个模块",
                        concepts=[
                            Concept(
                                concept_id="c-1-1-1-old",  # 非标准ID
                                name="概念1",
                                description="第一个概念",
                                estimated_hours=2.0,
                                prerequisites=[],
                            ),
                            Concept(
                                concept_id="c-1-1-2-new",  # 带-new后缀
                                name="概念2",
                                description="第二个概念",
                                estimated_hours=3.0,
                                prerequisites=["c-1-1-1-old"],  # 引用旧ID
                            ),
                        ],
                    ),
                ],
            ),
            Stage(
                stage_id="s-2",  # 标准ID
                name="阶段2",
                description="第二阶段",
                order=2,
                modules=[
                    Module(
                        module_id="m-2-1-new",  # 带-new后缀
                        name="模块2",
                        description="第二个模块",
                        concepts=[
                            Concept(
                                concept_id="c-2-1-1-new",  # 带-new后缀
                                name="概念3",
                                description="第三个概念",
                                estimated_hours=4.0,
                                prerequisites=["c-1-1-2-new"],  # 引用带-new的ID
                            ),
                        ],
                    ),
                ],
            ),
        ],
        total_estimated_hours=9.0,
        recommended_completion_weeks=2,
    )
    
    # 执行规范化
    normalized = normalize_framework_ids(framework)
    
    # 验证Stage ID
    assert normalized.stages[0].stage_id == "s-1"
    assert normalized.stages[1].stage_id == "s-2"
    
    # 验证Module ID
    assert normalized.stages[0].modules[0].module_id == "m-1-1"
    assert normalized.stages[1].modules[0].module_id == "m-2-1"
    
    # 验证Concept ID
    assert normalized.stages[0].modules[0].concepts[0].concept_id == "c-1-1-1"
    assert normalized.stages[0].modules[0].concepts[1].concept_id == "c-1-1-2"
    assert normalized.stages[1].modules[0].concepts[0].concept_id == "c-2-1-1"
    
    # 验证prerequisites已更新为新ID
    assert normalized.stages[0].modules[0].concepts[1].prerequisites == ["c-1-1-1"]
    assert normalized.stages[1].modules[0].concepts[0].prerequisites == ["c-1-1-2"]


def test_normalize_framework_ids_multiple_modules():
    """测试多个模块的ID规范化"""
    framework = RoadmapFramework(
        roadmap_id="test-roadmap-456",
        title="多模块测试",
        stages=[
            Stage(
                stage_id="s-1",
                name="阶段1",
                description="第一阶段",
                order=1,
                modules=[
                    Module(
                        module_id="m-1-1-new",
                        name="模块1",
                        description="第一个模块",
                        concepts=[
                            Concept(
                                concept_id="c-1-1-1-new",
                                name="概念1",
                                description="第一个概念",
                                estimated_hours=2.0,
                                prerequisites=[],
                            ),
                        ],
                    ),
                    Module(
                        module_id="m-1-2-new",
                        name="模块2",
                        description="第二个模块",
                        concepts=[
                            Concept(
                                concept_id="c-1-2-1-new",
                                name="概念2",
                                description="第二个概念",
                                estimated_hours=3.0,
                                prerequisites=["c-1-1-1-new"],
                            ),
                        ],
                    ),
                ],
            ),
        ],
        total_estimated_hours=5.0,
        recommended_completion_weeks=1,
    )
    
    normalized = normalize_framework_ids(framework)
    
    # 验证第二个模块的ID
    assert normalized.stages[0].modules[1].module_id == "m-1-2"
    assert normalized.stages[0].modules[1].concepts[0].concept_id == "c-1-2-1"
    
    # 验证prerequisites已更新
    assert normalized.stages[0].modules[1].concepts[0].prerequisites == ["c-1-1-1"]


def test_normalize_framework_ids_preserves_other_fields():
    """测试ID规范化不影响其他字段"""
    framework = RoadmapFramework(
        roadmap_id="test-roadmap-789",
        title="保留字段测试",
        stages=[
            Stage(
                stage_id="s-1-old",
                name="阶段1",
                description="第一阶段",
                order=1,
                modules=[
                    Module(
                        module_id="m-1-1-old",
                        name="模块1",
                        description="第一个模块",
                        concepts=[
                            Concept(
                                concept_id="c-1-1-1-old",
                                name="概念1",
                                description="第一个概念",
                                estimated_hours=2.0,
                                prerequisites=[],
                                difficulty="medium",
                                keywords=["关键词1", "关键词2"],
                                content_status="completed",
                                tutorial_id="tutorial-123",
                            ),
                        ],
                    ),
                ],
            ),
        ],
        total_estimated_hours=2.0,
        recommended_completion_weeks=1,
    )
    
    normalized = normalize_framework_ids(framework)
    
    # 验证其他字段未被修改
    concept = normalized.stages[0].modules[0].concepts[0]
    assert concept.name == "概念1"
    assert concept.description == "第一个概念"
    assert concept.estimated_hours == 2.0
    assert concept.difficulty == "medium"
    assert concept.keywords == ["关键词1", "关键词2"]
    assert concept.content_status == "completed"
    assert concept.tutorial_id == "tutorial-123"
    
    # 验证roadmap_id未被修改
    assert normalized.roadmap_id == "test-roadmap-789"
    assert normalized.title == "保留字段测试"


def test_normalize_framework_ids_empty_prerequisites():
    """测试空prerequisites列表"""
    framework = RoadmapFramework(
        roadmap_id="test-roadmap-000",
        title="空prerequisites测试",
        stages=[
            Stage(
                stage_id="s-1",
                name="阶段1",
                description="第一阶段",
                order=1,
                modules=[
                    Module(
                        module_id="m-1-1",
                        name="模块1",
                        description="第一个模块",
                        concepts=[
                            Concept(
                                concept_id="c-1-1-1-new",
                                name="概念1",
                                description="第一个概念",
                                estimated_hours=2.0,
                                prerequisites=[],  # 空列表
                            ),
                        ],
                    ),
                ],
            ),
        ],
        total_estimated_hours=2.0,
        recommended_completion_weeks=1,
    )
    
    normalized = normalize_framework_ids(framework)
    
    # 验证空prerequisites列表保持不变
    assert normalized.stages[0].modules[0].concepts[0].prerequisites == []
