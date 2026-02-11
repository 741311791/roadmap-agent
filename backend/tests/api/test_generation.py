"""
路线图生成API测试

测试端点：
- POST /api/v1/workflows/generation/generate - 生成路线图
- GET /api/v1/workflows/generation/{task_id}/status - 查询任务状态
- POST /api/v1/workflows/generation/{task_id}/cancel - 取消任务
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import User
from tests.api.base import APITestBase
from tests.api.factories import APIRequestFactory
from tests.api.mocks import APIMocks


class TestGenerateRoadmap(APITestBase):
    """测试路线图生成端点"""
    
    @pytest.mark.asyncio
    async def test_generate_roadmap_success(
        self, 
        client: AsyncClient,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试成功生成路线图
        
        验证：
        - 返回200状态码
        - 返回task_id
        - 返回roadmap_id
        """
        request_data = APIRequestFactory.create_generation_request()
        
        # Mock Celery任务
        with APIMocks.mock_celery_task("test-task-123"):
            response = await client.post(
                "/api/v1/workflows/generation/generate",
                json=request_data,
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        
        self.assert_success_response(data, expected_keys=["task_id", "status"])
        assert data["data"]["task_id"] is not None
        assert data["data"]["status"] == "pending"
        assert "message" in data["data"]
    
    @pytest.mark.asyncio
    async def test_generate_roadmap_without_user_id(self, client: AsyncClient, auth_headers: dict, initialized_orchestrator):
        """
        测试缺少user_id的生成请求
        
        验证：
        - 返回422状态码（验证错误）
        """
        request_data = APIRequestFactory.create_generation_request()
        # 移除user_id
        del request_data["user_id"]
        
        response = await client.post(
            "/api/v1/workflows/generation/generate",
            json=request_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_generate_roadmap_invalid_input(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """
        测试无效输入
        
        验证：
        - 返回422状态码（Validation Error）
        """
        invalid_data = {
            "preferences": {
                # 缺少必需字段
            }
        }
        
        response = await client.post(
            "/api/v1/workflows/generation/generate",
            json=invalid_data,
            headers=auth_headers,
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_generate_roadmap_with_additional_context(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        initialized_orchestrator
    ):
        """
        测试带额外上下文的生成
        
        验证：
        - 接受additional_context参数
        - 返回成功
        """
        request_data = APIRequestFactory.create_generation_request()
        request_data["additional_context"] = "专注于实战项目，减少理论部分"
        
        with APIMocks.mock_celery_task():
            response = await client.post(
                "/api/v1/workflows/generation/generate",
                json=request_data,
                headers=auth_headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["task_id"] is not None


class TestTaskStatus(APITestBase):
    """测试任务状态查询端点"""
    
    @pytest.mark.asyncio
    async def test_get_task_status_success(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        initialized_orchestrator
    ):
        """
        测试成功查询任务状态
        
        验证：
        - 返回200状态码
        - 包含status字段
        - 包含current_step字段
        """
        # 先创建一个任务
        from app.models.database import RoadmapTask
        from app.models.constants import TaskStatus
        import uuid
        
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.PROCESSING.value,
            current_step="intent_analysis",
        )
        
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        
        response = await client.get(
            f"/api/v1/roadmaps/{task.task_id}/status",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        self.assert_success_response(data, expected_keys=["status", "current_step"])
        assert data["data"]["status"] == TaskStatus.PROCESSING.value
        assert data["data"]["current_step"] == "intent_analysis"
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_get_task_status_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        initialized_orchestrator
    ):
        """
        测试查询不存在的任务
        
        验证：
        - 返回404状态码
        """
        response = await client.get(
            "/api/v1/workflows/generation/nonexistent-task-id/status",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_get_task_status_completed(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        initialized_orchestrator
    ):
        """
        测试查询已完成任务状态
        
        验证：
        - status为completed
        - 包含roadmap_id
        """
        from app.models.database import RoadmapTask
        from app.models.constants import TaskStatus
        import uuid
        
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.COMPLETED.value,
            current_step="completed",
        )
        
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        
        response = await client.get(
            f"/api/v1/workflows/generation/{task.task_id}/status",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["status"] == TaskStatus.COMPLETED.value
        assert data["data"]["roadmap_id"] == task.roadmap_id
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_get_task_status_failed(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        initialized_orchestrator
    ):
        """
        测试查询失败任务状态
        
        验证：
        - status为failed
        - 包含错误信息
        """
        from app.models.database import RoadmapTask
        from app.models.constants import TaskStatus
        import uuid
        
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.FAILED.value,
            current_step="intent_analysis",
            error_message="LLM调用失败",
        )
        
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        
        response = await client.get(
            f"/api/v1/workflows/generation/{task.task_id}/status",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["data"]["status"] == TaskStatus.FAILED.value
        assert "error_message" in data["data"]
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()


class TestCancelTask(APITestBase):
    """测试取消任务端点"""
    
    @pytest.mark.asyncio
    async def test_cancel_task_success(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        initialized_orchestrator
    ):
        """
        测试成功取消任务
        
        验证：
        - 返回200状态码
        - 任务状态变为cancelled
        """
        from app.models.database import RoadmapTask
        from app.models.constants import TaskStatus
        import uuid
        
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
        
        response = await client.post(
            f"/api/v1/workflows/generation/tasks/{task.task_id}/cancel",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        self.assert_success_response(data)
        
        # 验证任务状态已更新
        await test_session.refresh(task)
        assert task.status == TaskStatus.CANCELLED.value
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_cancel_task_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict,
        initialized_orchestrator
    ):
        """
        测试取消不存在的任务
        
        验证：
        - 返回404状态码
        """
        response = await client.post(
            "/api/v1/workflows/generation/tasks/nonexistent-task/cancel",
            headers=auth_headers,
        )
        
        assert response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_cancel_completed_task(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        initialized_orchestrator
    ):
        """
        测试取消已完成的任务
        
        验证：
        - 返回400或409状态码（不允许取消已完成的任务）
        """
        from app.models.database import RoadmapTask
        from app.models.constants import TaskStatus
        import uuid
        
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.COMPLETED.value,
            current_step="completed",
        )
        
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        
        response = await client.post(
            f"/api/v1/roadmaps/{task.task_id}/cancel",
            headers=auth_headers,
        )
        
        # 已完成的任务不应该被取消
        assert response.status_code in (400, 409)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_cancel_task_wrong_user(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        initialized_orchestrator
    ):
        """
        测试用户取消其他人的任务
        
        验证：
        - 返回403状态码（禁止访问）
        """
        from app.models.database import RoadmapTask
        from app.models.constants import TaskStatus
        import uuid
        
        # 创建属于其他用户的任务
        other_user_id = uuid.uuid4()
        
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=other_user_id,  # 不同的用户
            status=TaskStatus.PROCESSING.value,
            current_step="curriculum_design",
        )
        
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        
        response = await client.post(
            f"/api/v1/workflows/generation/tasks/{task.task_id}/cancel",
            headers=auth_headers,
        )
        
        # 不应该能取消其他用户的任务
        assert response.status_code == 403
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()

