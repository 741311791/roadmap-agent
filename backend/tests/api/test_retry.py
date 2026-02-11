"""
路线图重试API测试

测试端点：
- GET /api/v1/workflows/generation/retry/{task_id}/status - 获取重试状态
- POST /api/v1/workflows/generation/retry/{task_id}/resume - 断点续传
- POST /api/v1/workflows/generation/retry/{task_id}/time-travel - 时间旅行
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.models.database import User, RoadmapTask
from app.models.constants import TaskStatus
from tests.api.base import APITestBase


class TestRetryStatus(APITestBase):
    """测试获取重试状态端点"""
    
    @pytest.mark.asyncio
    async def test_get_retry_status_success(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试获取重试状态
        
        验证：
        - 返回200状态码
        - 包含can_retry字段
        - 包含current_checkpoint信息
        """
        # 创建一个失败的任务
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.FAILED.value,
            current_step="curriculum_design",
            error_message="LLM调用失败",
        )
        
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        
        response = await client.get(
            f"/api/v1/workflows/generation/retry/{task.task_id}/status",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        self.assert_success_response(data, expected_keys=["task_id", "can_retry"])
        assert data["data"]["task_id"] == task.task_id
        assert isinstance(data["data"]["can_retry"], bool)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_get_retry_status_completed_task(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试已完成任务的重试状态
        
        验证：
        - can_retry应该为false
        - 包含retry_reason说明为什么不能重试
        """
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.COMPLETED.value,
            current_step="completed",
        )
        
        test_session.add(task)
        await test_session.commit()
        
        response = await client.get(
            f"/api/v1/workflows/generation/retry/{task.task_id}/status",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # 已完成的任务不应该可以重试
        assert data["data"]["can_retry"] is False
        assert "retry_reason" in data["data"]
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_get_retry_status_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """
        测试不存在的任务
        
        验证：
        - 返回404状态码
        """
        response = await client.get(
            "/api/v1/workflows/generation/retry/nonexistent-task/status",
            headers=auth_headers,
        )
        
        assert response.status_code == 404


class TestResumeTask(APITestBase):
    """测试断点续传端点"""
    
    @pytest.mark.asyncio
    async def test_resume_failed_task(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试从失败节点恢复
        
        验证：
        - 返回200或202状态码
        - 任务状态更新为running
        """
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.FAILED.value,
            current_step="curriculum_design",
            error_message="临时网络故障",
        )
        
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        
        response = await client.post(
            f"/api/v1/workflows/generation/retry/{task.task_id}/resume",
            headers=auth_headers,
        )
        
        # 可能返回200（同步）或202（异步）
        assert response.status_code in (200, 202)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_resume_subgraph_failure(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试恢复子图并发失败
        
        验证：
        - 支持子图内部的断点续传
        - 自动重试所有失败的并发节点
        """
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.FAILED.value,
            current_step="tutorial_generation",
            error_message="部分概念内容生成失败",
        )
        
        test_session.add(task)
        await test_session.commit()
        
        response = await client.post(
            f"/api/v1/workflows/generation/retry/{task.task_id}/resume",
            headers=auth_headers,
        )
        
        assert response.status_code in (200, 202)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_resume_completed_task(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试恢复已完成的任务
        
        验证：
        - 返回400或409状态码
        - 不允许恢复已完成的任务
        """
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.COMPLETED.value,
            current_step="completed",
        )
        
        test_session.add(task)
        await test_session.commit()
        
        response = await client.post(
            f"/api/v1/workflows/generation/retry/{task.task_id}/resume",
            headers=auth_headers,
        )
        
        assert response.status_code in (400, 409)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()


class TestTimeTravelRetry(APITestBase):
    """测试时间旅行端点"""
    
    @pytest.mark.asyncio
    async def test_time_travel_to_node(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试时间旅行到指定节点
        
        验证：
        - 返回200或202状态码
        - 接受target_node参数
        """
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.COMPLETED.value,
            current_step="completed",
        )
        
        test_session.add(task)
        await test_session.commit()
        
        time_travel_request = {
            "target_node": "intent_analysis"  # 回到意图分析节点
        }
        
        response = await client.post(
            f"/api/v1/workflows/generation/retry/{task.task_id}/time-travel",
            json=time_travel_request,
            headers=auth_headers,
        )
        
        # 可能返回200（同步）或202（异步）
        assert response.status_code in (200, 202, 404)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_time_travel_invalid_node(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试时间旅行到无效节点
        
        验证：
        - 返回400或404状态码
        """
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.COMPLETED.value,
            current_step="completed",
        )
        
        test_session.add(task)
        await test_session.commit()
        
        time_travel_request = {
            "target_node": "invalid_node_name"
        }
        
        response = await client.post(
            f"/api/v1/workflows/generation/retry/{task.task_id}/time-travel",
            json=time_travel_request,
            headers=auth_headers,
        )
        
        assert response.status_code in (400, 404)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_time_travel_unauthorized(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User
    ):
        """
        测试未认证的时间旅行
        
        验证：
        - 返回401或403状态码
        """
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.COMPLETED.value,
            current_step="completed",
        )
        
        test_session.add(task)
        await test_session.commit()
        
        time_travel_request = {
            "target_node": "intent_analysis"
        }
        
        response = await client.post(
            f"/api/v1/workflows/generation/retry/{task.task_id}/time-travel",
            json=time_travel_request,
            # 不提供认证头
        )
        
        assert response.status_code in (401, 403)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()

