"""
集成测试 - Service层

测试目标：
- RetrievalService 查询逻辑
- ContentService 重试逻辑
- ConceptService 状态管理
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from datetime import datetime

from app.db.session import get_session
from app.services.retrieval_service import RetrievalService
from app.services.content_service import ContentService
from app.services.concept_service import ConceptService
from app.models.database import (
    RoadmapMetadata,
    ConceptMetadata,
    TutorialMetadata,
    User,
)
from app.core.auth.password import get_password_hash


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
    """
    创建测试路线图
    
    包含完整的Stage->Module->Concept层级结构
    """
    roadmap = RoadmapMetadata(
        roadmap_id=f"roadmap_{uuid.uuid4().hex[:8]}",
        user_id=str(test_user.id),
        title="Test Roadmap",
        curriculum_json={
            "stages": [
                {
                    "stage_id": "s1",
                    "name": "Stage 1",
                    "description": "Test Stage",
                    "order": 1,
                    "modules": [
                        {
                            "module_id": "m1",
                            "name": "Module 1",
                            "description": "Test Module",
                            "concepts": [
                                {
                                    "concept_id": "c1",
                                    "name": "Concept 1",
                                    "description": "Test Concept",
                                    "estimated_hours": 5.0,
                                    "prerequisites": [],
                                    "difficulty": "easy",
                                    "keywords": ["test"],
                                }
                            ],
                        }
                    ],
                }
            ],
            "total_estimated_hours": 5.0,
            "recommended_completion_weeks": 1,
        },
        status="completed",
        total_estimated_hours=5.0,
        recommended_completion_weeks=1,
        created_at=datetime.utcnow(),
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
        name="Concept 1",
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
# RetrievalService 测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_retrieval_service_get_roadmap_success(
    test_session: AsyncSession,
    test_roadmap: RoadmapMetadata,
):
    """
    测试RetrievalService获取路线图
    
    验证：
    - 可以成功获取已存在的路线图
    - 返回正确的数据结构
    """
    service = RetrievalService()
    
    result = await service.get_roadmap(
        db=test_session,
        roadmap_id=test_roadmap.roadmap_id,
    )
    
    assert result is not None
    assert result["roadmap_id"] == test_roadmap.roadmap_id
    assert result["title"] == test_roadmap.title
    assert result["status"] == test_roadmap.status


@pytest.mark.asyncio
@pytest.mark.integration
async def test_retrieval_service_get_nonexistent_roadmap(
    test_session: AsyncSession,
):
    """
    测试RetrievalService获取不存在的路线图
    
    验证：
    - 获取不存在的路线图返回None或抛出异常
    """
    service = RetrievalService()
    
    with pytest.raises(Exception):  # 根据实际实现可能是HTTPException或其他
        await service.get_roadmap(
            db=test_session,
            roadmap_id="nonexistent_roadmap_id",
        )


# ============================================================
# ConceptService 测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_concept_service_get_concept_from_roadmap(
    test_session: AsyncSession,
    test_roadmap: RoadmapMetadata,
    test_concept: ConceptMetadata,
):
    """
    测试ConceptService从路线图获取概念
    
    验证：
    - 可以从路线图JSON中提取概念
    - 返回正确的概念数据
    """
    service = ConceptService()
    
    concept_dict, metadata_dict, roadmap = await service.get_concept_from_roadmap(
        session=test_session,
        roadmap_id=test_roadmap.roadmap_id,
        concept_id="c1",
    )
    
    assert concept_dict is not None
    assert concept_dict["concept_id"] == "c1"
    assert concept_dict["name"] == "Concept 1"
    
    assert metadata_dict is not None
    assert metadata_dict["concept_id"] == "c1"
    
    assert roadmap is not None
    assert roadmap.roadmap_id == test_roadmap.roadmap_id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_concept_service_get_nonexistent_concept(
    test_session: AsyncSession,
    test_roadmap: RoadmapMetadata,
):
    """
    测试ConceptService获取不存在的概念
    
    验证：
    - 获取不存在的概念返回None
    """
    service = ConceptService()
    
    concept_dict, metadata_dict, roadmap = await service.get_concept_from_roadmap(
        session=test_session,
        roadmap_id=test_roadmap.roadmap_id,
        concept_id="nonexistent_concept",
    )
    
    # 不存在的概念应该返回None
    assert concept_dict is None


# ============================================================
# ContentService 测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_content_service_tutorial_generation_mock(
    test_session: AsyncSession,
    test_roadmap: RoadmapMetadata,
    test_concept: ConceptMetadata,
):
    """
    测试ContentService教程生成（Mock）
    
    验证：
    - 教程生成逻辑可以正常执行
    - 正确保存教程元数据
    """
    service = ContentService()
    
    # Mock TutorialGeneratorAgent
    mock_tutorial_output = MagicMock()
    mock_tutorial_output.tutorial_id = "tutorial_001"
    mock_tutorial_output.title = "Test Tutorial"
    mock_tutorial_output.summary = "Test Summary"
    mock_tutorial_output.content_url = "s3://test-bucket/tutorial.md"
    mock_tutorial_output.content_status = "completed"
    mock_tutorial_output.estimated_completion_time = 30
    mock_tutorial_output.generated_at = datetime.utcnow()
    
    with patch.object(service.tutorial_agent, "generate", return_value=mock_tutorial_output):
        # 执行教程生成
        result = await service.retry_tutorial_generation(
            session=test_session,
            roadmap_id=test_roadmap.roadmap_id,
            concept_id="c1",
            retry_reason="test",
        )
    
    assert result is not None
    assert result["tutorial_id"] == "tutorial_001"
    assert result["status"] == "completed"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_content_service_update_concept_status(
    test_session: AsyncSession,
    test_concept: ConceptMetadata,
):
    """
    测试ContentService更新概念状态
    
    验证：
    - 可以正确更新概念状态
    - 状态变更持久化到数据库
    """
    service = ContentService()
    
    # Mock通知服务避免WebSocket错误
    with patch.object(service.concept_service.notification, "send_concept_progress_event"):
        await service.concept_service.concept_crud.update_content_status(
            session=test_session,
            concept_id="c1",
            roadmap_id=test_concept.roadmap_id,
            content_type="tutorial",
            status="generating",
        )
    
    # 刷新概念元数据
    await test_session.refresh(test_concept)
    
    # 验证状态已更新
    assert test_concept.tutorial_status == "generating"


# ============================================================
# Service层错误处理测试
# ============================================================

@pytest.mark.asyncio
@pytest.mark.integration
async def test_service_handles_database_error_gracefully(
    test_session: AsyncSession,
):
    """
    测试Service层优雅处理数据库错误
    
    验证：
    - 数据库错误不会导致服务崩溃
    - 返回有意义的错误信息
    """
    service = RetrievalService()
    
    # 使用已关闭的session模拟数据库错误
    closed_session = AsyncMock()
    closed_session.execute.side_effect = Exception("Database connection lost")
    
    with pytest.raises(Exception) as exc_info:
        await service.get_roadmap(
            db=closed_session,
            roadmap_id="any_id",
        )
    
    # 验证错误信息有意义
    assert "Database" in str(exc_info.value) or "connection" in str(exc_info.value).lower()

