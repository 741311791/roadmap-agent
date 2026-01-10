"""
单元测试 - Schema验证

测试目标：
- Pydantic模型验证逻辑
- 数据类型转换
- 必填字段验证
"""
import pytest
from pydantic import ValidationError
from datetime import datetime

from app.models.domain import (
    LearningPreferences,
    UserRequest,
    Concept,
    Module,
    Stage,
    RoadmapFramework,
)


# ============================================================
# LearningPreferences 测试
# ============================================================

def test_learning_preferences_valid():
    """
    测试有效的学习偏好
    
    验证：
    - 所有必填字段都提供时可以正常创建
    - 字段类型正确
    """
    prefs = LearningPreferences(
        learning_goal="成为全栈开发工程师",
        available_hours_per_week=15,
        motivation="职业转型",
        current_level="beginner",
        career_background="市场营销",
        content_preference=["text", "hands_on"],
        target_deadline=None,
    )
    
    assert prefs.learning_goal == "成为全栈开发工程师"
    assert prefs.available_hours_per_week == 15
    assert prefs.current_level == "beginner"
    assert len(prefs.content_preference) == 2


def test_learning_preferences_missing_required_field():
    """
    测试缺少必填字段
    
    验证：
    - 缺少必填字段时抛出ValidationError
    """
    with pytest.raises(ValidationError) as exc_info:
        LearningPreferences(
            # 缺少learning_goal
            available_hours_per_week=15,
            motivation="职业转型",
            current_level="beginner",
        )
    
    errors = exc_info.value.errors()
    assert any(error["loc"][0] == "learning_goal" for error in errors)


def test_learning_preferences_invalid_type():
    """
    测试无效的字段类型
    
    验证：
    - 提供错误类型时抛出ValidationError
    """
    with pytest.raises(ValidationError):
        LearningPreferences(
            learning_goal="成为全栈开发工程师",
            available_hours_per_week="not_a_number",  # 应该是int
            motivation="职业转型",
            current_level="beginner",
            career_background="市场营销",
            content_preference=["text"],
        )


# ============================================================
# UserRequest 测试
# ============================================================

def test_user_request_valid():
    """
    测试有效的用户请求
    
    验证：
    - 包含LearningPreferences的嵌套结构可以正常创建
    """
    prefs = LearningPreferences(
        learning_goal="学习Python",
        available_hours_per_week=10,
        motivation="兴趣",
        current_level="beginner",
        career_background="学生",
        content_preference=["text"],
    )
    
    request = UserRequest(
        user_id="user_001",
        session_id="session_001",
        preferences=prefs,
        additional_context="希望快速入门",
    )
    
    assert request.user_id == "user_001"
    assert request.preferences.learning_goal == "学习Python"
    assert request.additional_context == "希望快速入门"


# ============================================================
# Concept 测试
# ============================================================

def test_concept_valid():
    """
    测试有效的概念模型
    
    验证：
    - 概念模型可以正常创建
    - 前置概念列表正确处理
    """
    concept = Concept(
        concept_id="c1",
        name="Python基础",
        description="学习Python基础语法",
        estimated_hours=8.0,
        prerequisites=[],
        difficulty="easy",
        keywords=["python", "basics"],
    )
    
    assert concept.concept_id == "c1"
    assert concept.estimated_hours == 8.0
    assert concept.difficulty == "easy"
    assert len(concept.prerequisites) == 0


def test_concept_with_prerequisites():
    """
    测试带前置概念的概念
    
    验证：
    - 前置概念列表可以正确设置
    """
    concept = Concept(
        concept_id="c2",
        name="Python进阶",
        description="学习Python进阶特性",
        estimated_hours=12.0,
        prerequisites=["c1"],  # 依赖c1
        difficulty="medium",
        keywords=["python", "advanced"],
    )
    
    assert len(concept.prerequisites) == 1
    assert concept.prerequisites[0] == "c1"


# ============================================================
# Module 测试
# ============================================================

def test_module_with_concepts():
    """
    测试包含概念的模块
    
    验证：
    - 模块可以包含多个概念
    - 嵌套结构正确
    """
    concept1 = Concept(
        concept_id="c1",
        name="HTML基础",
        description="HTML标签",
        estimated_hours=4.0,
        prerequisites=[],
        difficulty="easy",
        keywords=["html"],
    )
    
    concept2 = Concept(
        concept_id="c2",
        name="CSS基础",
        description="CSS样式",
        estimated_hours=6.0,
        prerequisites=["c1"],
        difficulty="easy",
        keywords=["css"],
    )
    
    module = Module(
        module_id="m1",
        name="Web基础",
        description="学习Web开发基础",
        concepts=[concept1, concept2],
    )
    
    assert module.module_id == "m1"
    assert len(module.concepts) == 2
    assert module.concepts[0].concept_id == "c1"
    assert module.concepts[1].concept_id == "c2"


# ============================================================
# Stage 测试
# ============================================================

def test_stage_with_modules():
    """
    测试包含模块的阶段
    
    验证：
    - 阶段可以包含多个模块
    - 完整的三层嵌套结构（Stage->Module->Concept）正确
    """
    concept = Concept(
        concept_id="c1",
        name="JavaScript基础",
        description="JS语法",
        estimated_hours=10.0,
        prerequisites=[],
        difficulty="medium",
        keywords=["javascript"],
    )
    
    module = Module(
        module_id="m1",
        name="前端编程",
        description="学习前端编程",
        concepts=[concept],
    )
    
    stage = Stage(
        stage_id="s1",
        name="前端基础",
        description="学习前端开发",
        order=1,
        modules=[module],
    )
    
    assert stage.stage_id == "s1"
    assert stage.order == 1
    assert len(stage.modules) == 1
    assert stage.modules[0].module_id == "m1"
    assert len(stage.modules[0].concepts) == 1


# ============================================================
# RoadmapFramework 测试
# ============================================================

def test_roadmap_framework_complete():
    """
    测试完整的路线图框架
    
    验证：
    - 完整的四层结构（Roadmap->Stage->Module->Concept）可以正常创建
    - 总时长和周数正确
    """
    concept = Concept(
        concept_id="c1",
        name="React基础",
        description="学习React",
        estimated_hours=15.0,
        prerequisites=[],
        difficulty="medium",
        keywords=["react"],
    )
    
    module = Module(
        module_id="m1",
        name="React开发",
        description="React框架",
        concepts=[concept],
    )
    
    stage = Stage(
        stage_id="s1",
        name="前端框架",
        description="学习前端框架",
        order=1,
        modules=[module],
    )
    
    roadmap = RoadmapFramework(
        roadmap_id="roadmap_001",
        title="前端开发学习路线",
        stages=[stage],
        total_estimated_hours=15.0,
        recommended_completion_weeks=2,
    )
    
    assert roadmap.roadmap_id == "roadmap_001"
    assert roadmap.title == "前端开发学习路线"
    assert roadmap.total_estimated_hours == 15.0
    assert roadmap.recommended_completion_weeks == 2
    assert len(roadmap.stages) == 1


def test_roadmap_framework_empty_stages():
    """
    测试空阶段列表
    
    验证：
    - 允许创建没有阶段的路线图（用于初始化）
    """
    roadmap = RoadmapFramework(
        roadmap_id="roadmap_002",
        title="空路线图",
        stages=[],
        total_estimated_hours=0.0,
        recommended_completion_weeks=0,
    )
    
    assert len(roadmap.stages) == 0
    assert roadmap.total_estimated_hours == 0.0

