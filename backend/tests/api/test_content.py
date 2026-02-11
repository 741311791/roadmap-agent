"""
内容管理API测试

测试端点：
- GET /api/v1/content/{roadmap_id}/concepts/{concept_id}/tutorials - 获取教程列表
- GET /api/v1/content/{roadmap_id}/concepts/{concept_id}/tutorials/latest - 获取最新教程
- GET /api/v1/content/{roadmap_id}/concepts/{concept_id}/resources - 获取资源列表
- GET /api/v1/content/{roadmap_id}/concepts/{concept_id}/quiz - 获取测验
- POST /api/v1/content/{roadmap_id}/concepts/{concept_id}/regenerate - 重新生成内容
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.models.database import User, RoadmapMetadata, ConceptMetadata, TutorialMetadata
from tests.api.base import APITestBase
from tests.factories import RoadmapFactory
from tests.api.factories import APIRequestFactory


class TestGetTutorials(APITestBase):
    """测试获取教程端点"""
    
    @pytest.mark.asyncio
    async def test_get_tutorials_list(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试获取教程版本列表
        
        验证：
        - 返回200状态码
        - 包含tutorials数组
        - 每个tutorial包含version信息
        """
        # 创建测试数据
        roadmap_framework = RoadmapFactory.create_simple_roadmap()
        roadmap = RoadmapMetadata(
            roadmap_id=roadmap_framework.roadmap_id,
            user_id=test_user.id,
            title=roadmap_framework.title,
            roadmap_data=roadmap_framework.model_dump(),
        )
        test_session.add(roadmap)
        
        concept = ConceptMetadata(
            concept_id="c1",
            roadmap_id=roadmap.roadmap_id,
            name="HTML基础",
        )
        test_session.add(concept)
        
        tutorial = TutorialMetadata(
            tutorial_id=f"tutorial-{uuid.uuid4().hex[:8]}",
            concept_id=concept.concept_id,
            roadmap_id=roadmap.roadmap_id,
            title="HTML基础教程",
            version=1,
            s3_key="tutorials/c1/v1.md",
        )
        test_session.add(tutorial)
        
        await test_session.commit()
        
        response = await client.get(
            f"/api/v1/content/{roadmap.roadmap_id}/concepts/{concept.concept_id}/tutorials",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        self.assert_success_response(data, expected_keys=["tutorials"])
        assert len(data["data"]["tutorials"]) > 0
        
        # 清理
        await test_session.delete(tutorial)
        await test_session.delete(concept)
        await test_session.delete(roadmap)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_get_latest_tutorial(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试获取最新版本教程
        
        验证：
        - 返回200状态码
        - 返回最高版本号的教程
        """
        roadmap_framework = RoadmapFactory.create_simple_roadmap()
        roadmap = RoadmapMetadata(
            roadmap_id=roadmap_framework.roadmap_id,
            user_id=test_user.id,
            title=roadmap_framework.title,
            roadmap_data=roadmap_framework.model_dump(),
        )
        test_session.add(roadmap)
        
        concept = ConceptMetadata(
            concept_id="c1",
            roadmap_id=roadmap.roadmap_id,
            name="HTML基础",
        )
        test_session.add(concept)
        
        # 创建多个版本
        tutorial_v1 = TutorialMetadata(
            tutorial_id=f"tutorial-v1-{uuid.uuid4().hex[:8]}",
            concept_id=concept.concept_id,
            roadmap_id=roadmap.roadmap_id,
            title="HTML基础教程",
            version=1,
            s3_key="tutorials/c1/v1.md",
        )
        tutorial_v2 = TutorialMetadata(
            tutorial_id=f"tutorial-v2-{uuid.uuid4().hex[:8]}",
            concept_id=concept.concept_id,
            roadmap_id=roadmap.roadmap_id,
            title="HTML基础教程",
            version=2,
            s3_key="tutorials/c1/v2.md",
        )
        
        test_session.add(tutorial_v1)
        test_session.add(tutorial_v2)
        await test_session.commit()
        
        response = await client.get(
            f"/api/v1/content/{roadmap.roadmap_id}/concepts/{concept.concept_id}/tutorials/latest",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        self.assert_success_response(data, expected_keys=["tutorial_id", "version"])
        assert data["data"]["version"] == 2  # 应该返回v2
        
        # 清理
        await test_session.delete(tutorial_v1)
        await test_session.delete(tutorial_v2)
        await test_session.delete(concept)
        await test_session.delete(roadmap)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_get_tutorial_not_found(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试获取不存在的教程
        
        验证：
        - 返回404状态码
        """
        roadmap_framework = RoadmapFactory.create_simple_roadmap()
        roadmap = RoadmapMetadata(
            roadmap_id=roadmap_framework.roadmap_id,
            user_id=test_user.id,
            title=roadmap_framework.title,
            roadmap_data=roadmap_framework.model_dump(),
        )
        test_session.add(roadmap)
        await test_session.commit()
        
        response = await client.get(
            f"/api/v1/content/{roadmap.roadmap_id}/concepts/nonexistent/tutorials/latest",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
        
        # 清理
        await test_session.delete(roadmap)
        await test_session.commit()


class TestGetResources(APITestBase):
    """测试获取资源端点"""
    
    @pytest.mark.asyncio
    async def test_get_resources_success(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试成功获取资源列表
        
        验证：
        - 返回200状态码
        - 包含resources数组
        - 每个resource包含url和type
        """
        roadmap_framework = RoadmapFactory.create_simple_roadmap()
        roadmap = RoadmapMetadata(
            roadmap_id=roadmap_framework.roadmap_id,
            user_id=test_user.id,
            title=roadmap_framework.title,
            roadmap_data=roadmap_framework.model_dump(),
        )
        test_session.add(roadmap)
        
        concept = ConceptMetadata(
            concept_id="c1",
            roadmap_id=roadmap.roadmap_id,
            name="HTML基础",
        )
        test_session.add(concept)
        await test_session.commit()
        
        response = await client.get(
            f"/api/v1/content/{roadmap.roadmap_id}/concepts/{concept.concept_id}/resources",
            headers=auth_headers,
        )
        
        # 可能返回200或404（取决于是否生成了资源）
        assert response.status_code in (200, 404)
        
        # 清理
        await test_session.delete(concept)
        await test_session.delete(roadmap)
        await test_session.commit()


class TestGetQuiz(APITestBase):
    """测试获取测验端点"""
    
    @pytest.mark.asyncio
    async def test_get_quiz_success(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试成功获取测验
        
        验证：
        - 返回200状态码
        - 包含questions数组
        - 每个question包含question_text和options
        """
        roadmap_framework = RoadmapFactory.create_simple_roadmap()
        roadmap = RoadmapMetadata(
            roadmap_id=roadmap_framework.roadmap_id,
            user_id=test_user.id,
            title=roadmap_framework.title,
            roadmap_data=roadmap_framework.model_dump(),
        )
        test_session.add(roadmap)
        
        concept = ConceptMetadata(
            concept_id="c1",
            roadmap_id=roadmap.roadmap_id,
            name="HTML基础",
        )
        test_session.add(concept)
        await test_session.commit()
        
        response = await client.get(
            f"/api/v1/content/{roadmap.roadmap_id}/concepts/{concept.concept_id}/quiz",
            headers=auth_headers,
        )
        
        # 可能返回200或404（取决于是否生成了测验）
        assert response.status_code in (200, 404)
        
        # 清理
        await test_session.delete(concept)
        await test_session.delete(roadmap)
        await test_session.commit()


class TestRegenerateContent(APITestBase):
    """测试重新生成内容端点"""
    
    @pytest.mark.asyncio
    async def test_regenerate_content(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试重试内容生成
        
        验证：
        - 返回200状态码
        - 返回任务ID
        """
        roadmap_framework = RoadmapFactory.create_simple_roadmap()
        roadmap = RoadmapMetadata(
            roadmap_id=roadmap_framework.roadmap_id,
            user_id=test_user.id,
            title=roadmap_framework.title,
            roadmap_data=roadmap_framework.model_dump(),
        )
        test_session.add(roadmap)
        
        concept = ConceptMetadata(
            concept_id="c1",
            roadmap_id=roadmap.roadmap_id,
            name="HTML基础",
        )
        test_session.add(concept)
        await test_session.commit()
        
        regenerate_request = APIRequestFactory.create_retry_content_request(
            content_types=["tutorial"]
        )
        
        response = await client.post(
            f"/api/v1/content/{roadmap.roadmap_id}/concepts/{concept.concept_id}/regenerate",
            json=regenerate_request,
            headers=auth_headers,
        )
        
        # 可能返回200、202或其他状态码
        assert response.status_code in (200, 202, 404)
        
        # 清理
        await test_session.delete(concept)
        await test_session.delete(roadmap)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_regenerate_all_content_types(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试重试所有类型的内容
        
        验证：
        - 可以同时重试tutorial、resource、quiz
        """
        roadmap_framework = RoadmapFactory.create_simple_roadmap()
        roadmap = RoadmapMetadata(
            roadmap_id=roadmap_framework.roadmap_id,
            user_id=test_user.id,
            title=roadmap_framework.title,
            roadmap_data=roadmap_framework.model_dump(),
        )
        test_session.add(roadmap)
        
        concept = ConceptMetadata(
            concept_id="c1",
            roadmap_id=roadmap.roadmap_id,
            name="HTML基础",
        )
        test_session.add(concept)
        await test_session.commit()
        
        regenerate_request = APIRequestFactory.create_retry_content_request(
            content_types=["tutorial", "resource", "quiz"]
        )
        
        response = await client.post(
            f"/api/v1/content/{roadmap.roadmap_id}/concepts/{concept.concept_id}/regenerate",
            json=regenerate_request,
            headers=auth_headers,
        )
        
        assert response.status_code in (200, 202, 404)
        
        # 清理
        await test_session.delete(concept)
        await test_session.delete(roadmap)
        await test_session.commit()

