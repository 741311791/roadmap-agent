"""
测试共享 Fixtures

提供所有测试所需的通用 fixtures 和 mock 对象。
"""
import pytest
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

# 设置测试环境变量（必须在导入app之前）
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/roadmap_test"
)
os.environ["SECRET_KEY"] = "test_secret_key_12345"
os.environ["ENABLE_TASK_RECOVERY"] = "false"
os.environ["ENABLE_TECH_ASSESSMENT_INIT"] = "false"

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
        content_preference=["text", "hands_on", "visual"],
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


# ============================================================
# 高级 Mock Fixtures（用于E2E测试）
# ============================================================

@pytest.fixture
def mock_all_llm_calls():
    """
    Mock所有LLM调用
    
    根据system_prompt自动判断是哪个Agent并返回相应的Mock响应
    """
    import json
    from tests.factories import MockResponseFactory
    
    async def async_mock_response(*args, **kwargs):
        """异步Mock响应"""
        messages = kwargs.get("messages", [])
        system_content = messages[0]["content"] if messages else ""
        
        # 根据system_prompt判断Agent类型
        if "意图分析" in system_content or "Intent Analysis" in system_content:
            response_data = MockResponseFactory.create_llm_intent_response()
        elif "课程架构师" in system_content or "Curriculum Architect" in system_content:
            response_data = MockResponseFactory.create_llm_curriculum_response()
        elif "验证" in system_content or "Validation" in system_content:
            response_data = MockResponseFactory.create_llm_validation_response()
        else:
            # 默认响应
            response_data = {"status": "success", "data": {}}
        
        # 创建Mock响应对象
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(response_data, ensure_ascii=False)
        return mock_response
    
    with patch("litellm.acompletion") as mock_completion:
        mock_completion.side_effect = async_mock_response
        yield mock_completion


@pytest.fixture
def mock_redis_pubsub():
    """Mock Redis Pub/Sub通知服务"""
    with patch("app.services.notification_service.notification_service") as mock:
        mock.publish_progress = AsyncMock()
        mock.publish_completed = AsyncMock()
        mock.publish_failed = AsyncMock()
        mock.send_human_review_request = AsyncMock()
        mock.send_concept_progress_event = AsyncMock()
        yield mock


@pytest.fixture
def mock_celery_task():
    """Mock Celery任务"""
    with patch("app.tasks.content_generation_tasks.generate_roadmap_content.delay") as mock:
        mock_result = MagicMock()
        mock_result.id = "test-celery-task-id"
        mock.return_value = mock_result
        yield mock


@pytest.fixture
def mock_s3_operations():
    """
    Mock S3操作（上传和下载）
    
    用于Mock教程、资源等内容的S3存储操作
    """
    with patch("app.tools.s3_storage_tool.S3StorageTool") as mock_s3:
        mock_instance = AsyncMock()
        
        # Mock上传操作
        async def mock_upload(*args, **kwargs):
            content = kwargs.get("content", "")
            key = kwargs.get("key", "test-key.md")
            return MagicMock(
                success=True,
                url=f"s3://test-bucket/{key}",
                key=key,
                size_bytes=len(content),
                etag="mock-etag",
            )
        
        # Mock下载操作
        async def mock_download(*args, **kwargs):
            return MagicMock(
                success=True,
                content="# 测试教程内容\n\n这是Mock的教程内容。",
                key="test-key.md",
            )
        
        mock_instance.upload.side_effect = mock_upload
        mock_instance.download.side_effect = mock_download
        mock_s3.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_tavily_search():
    """
    Mock Tavily搜索工具
    
    用于Mock资源推荐的搜索操作
    """
    with patch("app.tools.tavily_search_tool.TavilySearchTool") as mock_tavily:
        mock_instance = AsyncMock()
        
        async def mock_search(*args, **kwargs):
            return MagicMock(
                results=[
                    {
                        "title": "Mock搜索结果1",
                        "url": "https://example.com/1",
                        "content": "这是Mock的搜索结果内容1",
                        "score": 0.95,
                    },
                    {
                        "title": "Mock搜索结果2",
                        "url": "https://example.com/2",
                        "content": "这是Mock的搜索结果内容2",
                        "score": 0.88,
                    },
                ],
                query="test query",
            )
        
        mock_instance.search.side_effect = mock_search
        mock_tavily.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_tutorial_agent():
    """Mock教程生成Agent"""
    from tests.factories import ContentFactory
    
    with patch("app.agents.tutorial_generator.TutorialGeneratorAgent") as mock:
        mock_instance = AsyncMock()
        
        async def mock_generate(*args, **kwargs):
            concept = kwargs.get("concept") or args[0].concept
            return ContentFactory.create_tutorial_output(concept.concept_id)
        
        mock_instance.generate.side_effect = mock_generate
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_resource_agent():
    """Mock资源推荐Agent"""
    from tests.factories import ContentFactory
    
    with patch("app.agents.resource_recommender.ResourceRecommenderAgent") as mock:
        mock_instance = AsyncMock()
        
        async def mock_recommend(*args, **kwargs):
            concept = kwargs.get("concept") or args[0].concept
            return ContentFactory.create_resource_output(concept.concept_id)
        
        mock_instance.recommend.side_effect = mock_recommend
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_quiz_agent():
    """Mock测验生成Agent"""
    from tests.factories import ContentFactory
    
    with patch("app.agents.quiz_generator.QuizGeneratorAgent") as mock:
        mock_instance = AsyncMock()
        
        async def mock_generate(*args, **kwargs):
            concept = kwargs.get("concept") or args[0].concept
            return ContentFactory.create_quiz_output(concept.concept_id)
        
        mock_instance.generate.side_effect = mock_generate
        mock.return_value = mock_instance
        yield mock_instance


# ============================================================
# 测试数据库管理器初始化
# ============================================================

# ============================================================
# OrchestratorFactory 初始化（API测试需要）
# ============================================================

@pytest.fixture
async def initialized_orchestrator():
    """
    为需要OrchestratorFactory的测试初始化
    
    某些API端点（如status查询、cancel等）依赖WorkflowExecutor。
    使用function scope避免与事件循环冲突。
    """
    from app.core.orchestrator_factory import OrchestratorFactory
    
    try:
        # 如果已经初始化，直接返回
        if not OrchestratorFactory._initialized:
            await OrchestratorFactory.initialize()
        yield
        # 不在这里cleanup，因为可能被多个测试共享
    except Exception as e:
        # 如果初始化失败（如数据库未启动），跳过
        import warnings
        warnings.warn(f"OrchestratorFactory initialization failed: {e}")
        yield


# ============================================================
# 数据库会话 Fixtures（改进的清理策略）
# ============================================================

@pytest.fixture
async def test_session():
    """
    测试数据库会话fixture（改进版）
    
    核心改进：
    1. 使用应用的async_session_maker（避免创建新引擎）
    2. 在yield前后显式管理事务
    3. 确保在当前事件循环中完成清理
    """
    from app.db.session import async_session_maker
    
    async with async_session_maker() as session:
        try:
            # 开始事务
            await session.begin()
            yield session
        except Exception:
            # 出错时回滚
            await session.rollback()
            raise
        else:
            # 测试成功也回滚（保持数据隔离）
            await session.rollback()
        finally:
            # 确保会话关闭
            await session.close()


# ============================================================
# OrchestratorFactory 初始化 Fixture
# ============================================================

@pytest.fixture(scope="session", autouse=False)
async def initialize_orchestrator_factory():
    """
    初始化 OrchestratorFactory（测试会话级别）
    
    这个 fixture 会在需要时运行，用于测试需要orchestrator的场景。
    大多数测试不需要初始化orchestrator。
    """
    from app.core.orchestrator_factory import OrchestratorFactory
    
    # 初始化 OrchestratorFactory
    try:
        await OrchestratorFactory.initialize()
        yield
        # 清理（关闭 checkpointer）
        await OrchestratorFactory.cleanup()
    except Exception as e:
        # 如果初始化失败（比如数据库未启动），跳过这个fixture
        print(f"Warning: OrchestratorFactory initialization failed: {e}")
        yield
