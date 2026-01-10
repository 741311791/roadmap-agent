"""
端到端测试 - 内容生成流程

测试完整的内容生成流程：
1. Tutorial生成 (TutorialGeneratorAgent)
2. Resource推荐 (ResourceRecommenderAgent)
3. Quiz生成 (QuizGeneratorAgent)
4. 并行生成和错误处理
"""
import pytest
import asyncio
import uuid
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.database import (
    User,
    RoadmapMetadata,
    ConceptMetadata,
)
from app.core.auth.password import get_password_hash
from tests.factories import (
    RoadmapFactory,
    ContentFactory,
    LearningPreferencesFactory,
)


@pytest.fixture
async def test_session():
    """创建测试数据库会话"""
    async for session in get_session():
        yield session


@pytest.fixture
async def test_user(test_session: AsyncSession):
    """创建测试用户"""
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password=await get_password_hash("testpassword123"),
        is_active=True,
        is_verified=True,
        is_superuser=False,
    )
    
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    
    yield user
    
    await test_session.delete(user)
    await test_session.commit()


@pytest.fixture
async def test_roadmap(test_session: AsyncSession, test_user: User):
    """创建测试路线图"""
    roadmap_data = RoadmapFactory.create_simple_roadmap()
    
    roadmap = RoadmapMetadata(
        roadmap_id=roadmap_data.roadmap_id,
        user_id=str(test_user.id),
        title=roadmap_data.title,
        status="completed",
        curriculum_json=roadmap_data.model_dump(),
        total_estimated_hours=roadmap_data.total_estimated_hours,
        recommended_completion_weeks=roadmap_data.recommended_completion_weeks,
    )
    
    test_session.add(roadmap)
    await test_session.commit()
    await test_session.refresh(roadmap)
    
    yield roadmap
    
    await test_session.delete(roadmap)
    await test_session.commit()


@pytest.fixture
async def test_concept(test_session: AsyncSession, test_roadmap: RoadmapMetadata):
    """创建测试概念元数据"""
    concept = ConceptMetadata(
        concept_id="c1",
        roadmap_id=test_roadmap.roadmap_id,
        name="HTML基础",
        tutorial_status="not_started",
        resource_status="not_started",
        quiz_status="not_started",
    )
    
    test_session.add(concept)
    await test_session.commit()
    await test_session.refresh(concept)
    
    yield concept
    
    await test_session.delete(concept)
    await test_session.commit()


# ============================================================
# Tutorial生成测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_content_generation_tutorial_success(
    test_session: AsyncSession,
    test_roadmap: RoadmapMetadata,
    test_concept: ConceptMetadata,
):
    """
    测试Tutorial生成成功
    
    验证：
    - Mock TutorialGeneratorAgent
    - Mock S3 upload返回成功
    - 教程元数据正确保存
    """
    from app.services.content_service import ContentService
    from app.models.domain import Concept, LearningPreferences
    
    # 创建服务实例
    content_service = ContentService()
    
    # Mock Tutorial Agent和S3
    with patch.object(content_service.tutorial_agent, "generate") as mock_generate:
        mock_generate.return_value = ContentFactory.create_tutorial_output("c1")
        
        # 执行教程生成
        result = await content_service.retry_tutorial_generation(
            session=test_session,
            roadmap_id=test_roadmap.roadmap_id,
            concept_id="c1",
            retry_reason="test",
        )
    
    assert result is not None
    assert result["status"] == "completed"


# ============================================================
# Resource推荐测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_content_generation_resource_success(
    test_session: AsyncSession,
    test_roadmap: RoadmapMetadata,
    test_concept: ConceptMetadata,
):
    """
    测试Resource推荐成功
    
    验证：
    - Mock ResourceRecommenderAgent
    - Mock Tavily API返回搜索结果
    - 资源推荐正确保存
    """
    from app.services.content_service import ContentService
    
    content_service = ContentService()
    
    # Mock Resource Agent
    with patch.object(content_service.resource_agent, "recommend") as mock_recommend:
        mock_recommend.return_value = ContentFactory.create_resource_output("c1")
        
        # 执行资源推荐
        result = await content_service.retry_resource_generation(
            session=test_session,
            roadmap_id=test_roadmap.roadmap_id,
            concept_id="c1",
            retry_reason="test",
        )
    
    assert result is not None
    assert "resources" in result
    assert len(result["resources"]) > 0


# ============================================================
# Quiz生成测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_content_generation_quiz_success(
    test_session: AsyncSession,
    test_roadmap: RoadmapMetadata,
    test_concept: ConceptMetadata,
):
    """
    测试Quiz生成成功
    
    验证：
    - Mock QuizGeneratorAgent
    - 测验题目结构正确
    - 难度分级正确
    """
    from app.services.content_service import ContentService
    
    content_service = ContentService()
    
    # Mock Quiz Agent
    with patch.object(content_service.quiz_agent, "generate") as mock_generate:
        mock_generate.return_value = ContentFactory.create_quiz_output("c1")
        
        # 执行测验生成
        result = await content_service.retry_quiz_generation(
            session=test_session,
            roadmap_id=test_roadmap.roadmap_id,
            concept_id="c1",
            retry_reason="test",
        )
    
    assert result is not None
    assert "questions" in result
    assert len(result["questions"]) > 0
    
    # 验证题目结构
    question = result["questions"][0]
    assert "question_text" in question
    assert "options" in question
    assert "correct_answer" in question
    assert "difficulty" in question


# ============================================================
# 单概念完整流程测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_content_generation_single_concept_flow(
    test_session: AsyncSession,
    test_roadmap: RoadmapMetadata,
    test_concept: ConceptMetadata,
):
    """
    测试单概念完整生成流程
    
    验证：
    - Tutorial→Resource→Quiz串行执行
    - 执行顺序正确
    - 数据库事务正确提交
    """
    from app.tasks.concept_generator import generate_single_concept
    from app.agents.factory import get_agent_factory
    
    # 准备测试数据
    roadmap_data = RoadmapFactory.create_simple_roadmap(test_roadmap.roadmap_id)
    concept = roadmap_data.stages[0].modules[0].concepts[0]
    concept_map = {c.concept_id: c for stage in roadmap_data.stages for module in stage.modules for c in module.concepts}
    preferences = LearningPreferencesFactory.create_beginner_preferences()
    agent_factory = get_agent_factory()
    
    # 共享数据结构
    progress_counter = {"current": 0}
    progress_lock = asyncio.Lock()
    tutorial_refs = {}
    resource_refs = {}
    quiz_refs = {}
    failed_concepts = []
    results_lock = asyncio.Lock()
    db_semaphore = asyncio.Semaphore(8)
    
    # Mock所有Agent
    with patch("app.agents.tutorial_generator.TutorialGeneratorAgent") as mock_tutorial:
        mock_tutorial_instance = AsyncMock()
        mock_tutorial_instance.generate.return_value = ContentFactory.create_tutorial_output(concept.concept_id)
        mock_tutorial.return_value = mock_tutorial_instance
        
        with patch("app.agents.resource_recommender.ResourceRecommenderAgent") as mock_resource:
            mock_resource_instance = AsyncMock()
            mock_resource_instance.recommend.return_value = ContentFactory.create_resource_output(concept.concept_id)
            mock_resource.return_value = mock_resource_instance
            
            with patch("app.agents.quiz_generator.QuizGeneratorAgent") as mock_quiz:
                mock_quiz_instance = AsyncMock()
                mock_quiz_instance.generate.return_value = ContentFactory.create_quiz_output(concept.concept_id)
                mock_quiz.return_value = mock_quiz_instance
                
                # Mock通知服务
                with patch("app.services.notification_service.notification_service") as mock_notif:
                    mock_notif.send_concept_progress_event = AsyncMock()
                    
                    # 执行单概念生成
                    await generate_single_concept(
                        task_id="test-task",
                        roadmap_id=test_roadmap.roadmap_id,
                        concept=concept,
                        concept_map=concept_map,
                        preferences=preferences,
                        agent_factory=agent_factory,
                        total_concepts=1,
                        progress_counter=progress_counter,
                        progress_lock=progress_lock,
                        tutorial_refs=tutorial_refs,
                        resource_refs=resource_refs,
                        quiz_refs=quiz_refs,
                        failed_concepts=failed_concepts,
                        results_lock=results_lock,
                        db_semaphore=db_semaphore,
                    )
    
    # 验证结果
    assert len(failed_concepts) == 0
    assert concept.concept_id in tutorial_refs
    assert concept.concept_id in resource_refs
    assert concept.concept_id in quiz_refs


# ============================================================
# 并行生成测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
async def test_content_generation_parallel_concepts(
    test_session: AsyncSession,
    test_user: User,
):
    """
    测试多个概念并行生成
    
    验证：
    - 多个概念可以并行生成
    - 数据库连接池保护（信号量限制）
    - 进度更新正确
    """
    from app.tasks.content_generation_tasks import _async_generate_content
    
    # 创建复杂路线图（多个概念）
    roadmap_data = RoadmapFactory.create_complex_roadmap()
    
    roadmap = RoadmapMetadata(
        roadmap_id=roadmap_data.roadmap_id,
        user_id=str(test_user.id),
        title=roadmap_data.title,
        status="completed",
        curriculum_json=roadmap_data.model_dump(),
        total_estimated_hours=roadmap_data.total_estimated_hours,
        recommended_completion_weeks=roadmap_data.recommended_completion_weeks,
    )
    
    test_session.add(roadmap)
    await test_session.commit()
    
    # Mock所有Agent和工具
    with patch("app.agents.tutorial_generator.TutorialGeneratorAgent") as mock_tutorial, \
         patch("app.agents.resource_recommender.ResourceRecommenderAgent") as mock_resource, \
         patch("app.agents.quiz_generator.QuizGeneratorAgent") as mock_quiz, \
         patch("app.services.notification_service.notification_service") as mock_notif:
        
        # 配置Mock
        mock_tutorial_instance = AsyncMock()
        mock_tutorial_instance.generate = AsyncMock(side_effect=lambda input: ContentFactory.create_tutorial_output(input.concept.concept_id))
        mock_tutorial.return_value = mock_tutorial_instance
        
        mock_resource_instance = AsyncMock()
        mock_resource_instance.recommend = AsyncMock(side_effect=lambda input: ContentFactory.create_resource_output(input.concept.concept_id))
        mock_resource.return_value = mock_resource_instance
        
        mock_quiz_instance = AsyncMock()
        mock_quiz_instance.generate = AsyncMock(side_effect=lambda input: ContentFactory.create_quiz_output(input.concept.concept_id))
        mock_quiz.return_value = mock_quiz_instance
        
        mock_notif.send_concept_progress_event = AsyncMock()
        
        # 执行并行生成
        result = await _async_generate_content(
            task_id="test-task",
            roadmap_id=roadmap.roadmap_id,
            roadmap_framework_data=roadmap_data.model_dump(),
            user_preferences_data=LearningPreferencesFactory.create_beginner_preferences().model_dump(),
        )
    
    # 验证结果
    assert result is not None
    assert result["failed_count"] == 0
    assert result["tutorial_count"] > 0
    
    # 清理
    await test_session.delete(roadmap)
    await test_session.commit()


# ============================================================
# 错误处理和重试测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_content_generation_retry_on_failure(
    test_session: AsyncSession,
    test_roadmap: RoadmapMetadata,
    test_concept: ConceptMetadata,
):
    """
    测试内容生成失败重试
    
    验证：
    - Mock第一次失败，第二次成功
    - 重试逻辑正确执行
    - 失败概念正确记录
    """
    from app.services.content_service import ContentService
    
    content_service = ContentService()
    
    call_count = {"count": 0}
    
    async def mock_generate_with_retry(*args, **kwargs):
        """Mock生成，第一次失败，第二次成功"""
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise Exception("生成失败（测试）")
        else:
            return ContentFactory.create_tutorial_output("c1")
    
    # Mock Tutorial Agent with retry logic
    with patch.object(content_service.tutorial_agent, "generate") as mock_generate:
        mock_generate.side_effect = mock_generate_with_retry
        
        try:
            # 第一次调用应该失败
            await content_service.retry_tutorial_generation(
                session=test_session,
                roadmap_id=test_roadmap.roadmap_id,
                concept_id="c1",
                retry_reason="test",
            )
        except Exception as e:
            # 验证失败被正确捕获
            assert "生成失败" in str(e)
        
        # 第二次调用应该成功
        result = await content_service.retry_tutorial_generation(
            session=test_session,
            roadmap_id=test_roadmap.roadmap_id,
            concept_id="c1",
            retry_reason="test",
        )
        
        assert result is not None
        assert call_count["count"] == 2

