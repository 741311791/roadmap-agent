"""
测试共享 Fixtures

提供所有测试所需的通用 fixtures 和 mock 对象。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.models.domain import (
    UserRequest,
    LearningPreferences,
    IntentAnalysisOutput,
    RoadmapFramework,
    Stage,
    Module,
    Concept,
    ValidationOutput,
    ValidationIssue,
    TutorialGenerationOutput,
)


# ============================================================
# 基础数据 Fixtures
# ============================================================

@pytest.fixture
def sample_learning_preferences() -> LearningPreferences:
    """示例学习偏好"""
    return LearningPreferences(
        learning_goal="成为全栈 Web 开发工程师",
        available_hours_per_week=15,
        motivation="转行进入技术领域",
        current_level="beginner",
        career_background="市场营销 3 年经验",
        content_preference=["text", "interactive", "project"],
        target_deadline=None,
    )


@pytest.fixture
def sample_user_request(sample_learning_preferences) -> UserRequest:
    """示例用户请求"""
    return UserRequest(
        user_id="test-user-001",
        session_id="test-session-001",
        preferences=sample_learning_preferences,
        additional_context="希望能在 6 个月内找到初级开发工作",
    )


@pytest.fixture
def sample_intent_analysis() -> IntentAnalysisOutput:
    """示例需求分析结果"""
    return IntentAnalysisOutput(
        parsed_goal="系统学习全栈 Web 开发，从前端基础到后端 API 开发",
        key_technologies=["HTML", "CSS", "JavaScript", "React", "Node.js", "PostgreSQL"],
        difficulty_profile="零基础学习者，需要从基础概念开始，循序渐进",
        time_constraint="每周 15 小时，预计 6 个月完成基础学习",
        recommended_focus=["前端基础", "JavaScript 核心", "React 框架", "后端入门"],
    )


@pytest.fixture
def sample_concept() -> Concept:
    """示例概念"""
    return Concept(
        concept_id="concept-html-basics",
        name="HTML 基础",
        description="学习 HTML 文档结构、常用标签和语义化",
        estimated_hours=4.0,
        prerequisites=[],
        difficulty="easy",
        keywords=["HTML", "标签", "文档结构"],
    )


@pytest.fixture
def sample_module(sample_concept) -> Module:
    """示例模块"""
    return Module(
        module_id="module-web-basics",
        name="Web 基础",
        description="学习 Web 开发的基础知识",
        concepts=[sample_concept],
    )


@pytest.fixture
def sample_stage(sample_module) -> Stage:
    """示例阶段"""
    return Stage(
        stage_id="stage-frontend-basics",
        name="前端基础",
        description="学习前端开发的基础技术",
        order=1,
        modules=[sample_module],
    )


@pytest.fixture
def sample_roadmap_framework() -> RoadmapFramework:
    """示例路线图框架"""
    concept1 = Concept(
        concept_id="c1",
        name="HTML 基础",
        description="HTML 文档结构和标签",
        estimated_hours=4.0,
        prerequisites=[],
        difficulty="easy",
        keywords=["HTML"],
    )
    concept2 = Concept(
        concept_id="c2",
        name="CSS 基础",
        description="CSS 选择器和样式",
        estimated_hours=6.0,
        prerequisites=["c1"],
        difficulty="easy",
        keywords=["CSS"],
    )
    concept3 = Concept(
        concept_id="c3",
        name="JavaScript 基础",
        description="JS 语法和 DOM 操作",
        estimated_hours=10.0,
        prerequisites=["c1", "c2"],
        difficulty="medium",
        keywords=["JavaScript"],
    )
    
    module1 = Module(
        module_id="m1",
        name="Web 基础",
        description="HTML 和 CSS 基础",
        concepts=[concept1, concept2],
    )
    module2 = Module(
        module_id="m2",
        name="JavaScript 入门",
        description="JavaScript 编程基础",
        concepts=[concept3],
    )
    
    stage1 = Stage(
        stage_id="s1",
        name="前端基础",
        description="前端开发基础知识",
        order=1,
        modules=[module1, module2],
    )
    
    return RoadmapFramework(
        roadmap_id="roadmap-001",
        title="全栈 Web 开发学习路线",
        stages=[stage1],
        total_estimated_hours=20.0,
        recommended_completion_weeks=4,
    )


@pytest.fixture
def sample_validation_output_valid() -> ValidationOutput:
    """示例验证结果（通过）"""
    return ValidationOutput(
        is_valid=True,
        issues=[],
        overall_score=95.0,
    )


@pytest.fixture
def sample_validation_output_invalid() -> ValidationOutput:
    """示例验证结果（未通过）"""
    return ValidationOutput(
        is_valid=False,
        issues=[
            ValidationIssue(
                severity="critical",
                location="Stage 1 > Module 1",
                issue="概念缺少必要的前置关系",
                suggestion="添加 HTML 基础作为 CSS 的前置概念",
            ),
            ValidationIssue(
                severity="warning",
                location="Stage 1",
                issue="阶段内容过于简单",
                suggestion="增加更多实践项目",
            ),
        ],
        overall_score=65.0,
    )


@pytest.fixture
def sample_tutorial_output() -> TutorialGenerationOutput:
    """示例教程生成输出"""
    return TutorialGenerationOutput(
        concept_id="c1",
        tutorial_id="tutorial-001",
        title="HTML 基础入门教程",
        summary="本教程将带你从零开始学习 HTML，包括文档结构、常用标签和语义化实践。",
        content_url="s3://roadmap-content/tutorials/c1/v1.md",
        content_status="completed",
        estimated_completion_time=45,
        generated_at=datetime.now(),
    )


# ============================================================
# Mock Fixtures
# ============================================================

@pytest.fixture
def mock_llm_response():
    """Mock LLM 响应工厂"""
    def _create_response(content: str):
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = content
        return response
    return _create_response


@pytest.fixture
def mock_litellm(mock_llm_response):
    """Mock LiteLLM 调用"""
    with patch("litellm.acompletion") as mock:
        mock.return_value = mock_llm_response('{"test": "response"}')
        yield mock


@pytest.fixture
def mock_s3_tool():
    """Mock S3 Storage Tool"""
    with patch("app.core.tool_registry.tool_registry") as mock_registry:
        mock_s3 = AsyncMock()
        mock_s3.execute.return_value = MagicMock(
            success=True,
            url="s3://test-bucket/test-key.md",
            key="test-key.md",
            size_bytes=1024,
            etag="test-etag",
        )
        mock_registry.get.return_value = mock_s3
        yield mock_s3


@pytest.fixture
def mock_web_search_tool():
    """Mock Web Search Tool"""
    with patch("app.core.tool_registry.tool_registry") as mock_registry:
        mock_search = AsyncMock()
        mock_search.execute.return_value = MagicMock(
            results=[
                {"title": "Test Result", "url": "https://example.com", "snippet": "Test snippet"}
            ],
            total_found=1,
        )
        mock_registry.get.return_value = mock_search
        yield mock_search

