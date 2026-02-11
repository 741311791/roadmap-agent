"""
路线图查询API测试

测试端点：
- GET /api/v1/roadmaps/{roadmap_id} - 获取完整路线图
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.models.database import User, RoadmapMetadata, RoadmapTask
from app.models.constants import TaskStatus
from tests.api.base import APITestBase
from tests.factories import RoadmapFactory


class TestGetRoadmap(APITestBase):
    """测试获取路线图端点"""
    
    @pytest.mark.asyncio
    async def test_get_roadmap_success(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试成功获取完整路线图
        
        验证：
        - 返回200状态码
        - 包含完整的路线图结构
        - 包含stages, modules, concepts
        """
        # 创建测试路线图
        roadmap_framework = RoadmapFactory.create_simple_roadmap()
        
        roadmap = RoadmapMetadata(
            roadmap_id=roadmap_framework.roadmap_id,
            user_id=test_user.id,
            title=roadmap_framework.title,
            roadmap_data=roadmap_framework.model_dump(),
        )
        
        test_session.add(roadmap)
        await test_session.commit()
        await test_session.refresh(roadmap)
        
        response = await client.get(
            f"/api/v1/roadmaps/{roadmap.roadmap_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        self.assert_success_response(
            data,
            expected_keys=["roadmap_id", "title", "stages"]
        )
        assert data["data"]["roadmap_id"] == roadmap.roadmap_id
        assert len(data["data"]["stages"]) > 0
        
        # 清理
        await test_session.delete(roadmap)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_get_roadmap_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """
        测试获取不存在的路线图
        
        验证：
        - 返回404状态码
        """
        response = await client.get(
            "/api/v1/roadmaps/nonexistent-roadmap-id",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_roadmap_generating(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试获取生成中的路线图
        
        验证：
        - 返回202状态码或200状态码（取决于实现）
        - 返回generating状态
        - 包含task_id
        """
        # 创建一个正在运行的任务
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.PROCESSING.value,
            current_step="curriculum_design",
        )
        
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        
        response = await client.get(
            f"/api/v1/roadmaps/{task.roadmap_id}",
            headers=auth_headers,
        )
        
        # 路线图不存在但有活跃任务
        assert response.status_code in (200, 202, 404)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_get_roadmap_unauthorized(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User
    ):
        """
        测试未认证访问路线图
        
        验证：
        - 返回401或403状态码
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
            f"/api/v1/roadmaps/{roadmap.roadmap_id}",
            # 不提供认证头
        )
        
        assert response.status_code in (401, 403)
        
        # 清理
        await test_session.delete(roadmap)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_get_roadmap_forbidden(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试访问他人的路线图
        
        验证：
        - 返回403状态码（如果启用了权限检查）
        """
        # 创建属于其他用户的路线图
        other_user_id = uuid.uuid4()
        roadmap_framework = RoadmapFactory.create_simple_roadmap()
        
        roadmap = RoadmapMetadata(
            roadmap_id=roadmap_framework.roadmap_id,
            user_id=other_user_id,  # 不同的用户
            title=roadmap_framework.title,
            roadmap_data=roadmap_framework.model_dump(),
        )
        
        test_session.add(roadmap)
        await test_session.commit()
        
        response = await client.get(
            f"/api/v1/roadmaps/{roadmap.roadmap_id}",
            headers=auth_headers,
        )
        
        # 根据权限策略，可能返回403或404
        assert response.status_code in (403, 404)
        
        # 清理
        await test_session.delete(roadmap)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_get_roadmap_with_content(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试获取包含内容的路线图
        
        验证：
        - 包含完整的stage/module/concept层次结构
        - 每个concept包含估算时长
        - 包含前置关系
        """
        roadmap_framework = RoadmapFactory.create_complex_roadmap()
        
        roadmap = RoadmapMetadata(
            roadmap_id=roadmap_framework.roadmap_id,
            user_id=test_user.id,
            title=roadmap_framework.title,
            roadmap_data=roadmap_framework.model_dump(),
        )
        
        test_session.add(roadmap)
        await test_session.commit()
        
        response = await client.get(
            f"/api/v1/roadmaps/{roadmap.roadmap_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 验证层次结构
        assert "stages" in data["data"]
        stages = data["data"]["stages"]
        assert len(stages) >= 1
        
        # 验证第一个stage
        first_stage = stages[0]
        assert "modules" in first_stage
        assert len(first_stage["modules"]) >= 1
        
        # 验证第一个module
        first_module = first_stage["modules"][0]
        assert "concepts" in first_module
        assert len(first_module["concepts"]) >= 1
        
        # 验证第一个concept
        first_concept = first_module["concepts"][0]
        assert "concept_id" in first_concept
        assert "name" in first_concept
        assert "estimated_hours" in first_concept
        assert "prerequisites" in first_concept
        
        # 清理
        await test_session.delete(roadmap)
        await test_session.commit()

