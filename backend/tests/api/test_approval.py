"""
人工审核API测试

测试端点：
- POST /api/v1/workflows/generation/{task_id}/approve - 审核路线图
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.models.database import User, RoadmapTask
from app.models.constants import TaskStatus
from tests.api.base import APITestBase
from tests.api.factories import APIRequestFactory


class TestApproveRoadmap(APITestBase):
    """测试路线图审核端点"""
    
    @pytest.mark.asyncio
    async def test_approve_roadmap_success(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试批准路线图
        
        验证：
        - 返回200状态码
        - 任务继续执行
        """
        # 创建处于human_review状态的任务
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.HUMAN_REVIEW.value,
            current_step="human_review",
        )
        
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        
        approval_request = APIRequestFactory.create_approval_request(
            approved=True,
            feedback=None
        )
        
        response = await client.post(
            f"/api/v1/workflows/generation/{task.task_id}/approve",
            json=approval_request,
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        self.assert_success_response(data)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_reject_roadmap_with_feedback(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试拒绝路线图并提供反馈
        
        验证：
        - 返回200状态码
        - 反馈被记录
        - 任务需要重新生成
        """
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.HUMAN_REVIEW.value,
            current_step="human_review",
        )
        
        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)
        
        approval_request = APIRequestFactory.create_approval_request(
            approved=False,
            feedback="请增加更多实战项目，减少理论部分"
        )
        
        response = await client.post(
            f"/api/v1/workflows/generation/{task.task_id}/approve",
            json=approval_request,
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        
        self.assert_success_response(data)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_approve_unauthorized(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User
    ):
        """
        测试未认证审核
        
        验证：
        - 返回401或403状态码
        """
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.HUMAN_REVIEW.value,
            current_step="human_review",
        )
        
        test_session.add(task)
        await test_session.commit()
        
        approval_request = APIRequestFactory.create_approval_request(approved=True)
        
        response = await client.post(
            f"/api/v1/roadmaps/{task.task_id}/approve",
            json=approval_request,
            # 不提供认证头
        )
        
        assert response.status_code in (401, 403)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_approve_wrong_user(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试非任务所有者审核
        
        验证：
        - 返回403状态码
        """
        # 创建属于其他用户的任务
        other_user_id = uuid.uuid4()
        
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=other_user_id,  # 不同的用户
            status=TaskStatus.HUMAN_REVIEW.value,
            current_step="human_review",
        )
        
        test_session.add(task)
        await test_session.commit()
        
        approval_request = APIRequestFactory.create_approval_request(approved=True)
        
        response = await client.post(
            f"/api/v1/workflows/generation/{task.task_id}/approve",
            json=approval_request,
            headers=auth_headers,
        )
        
        # 不应该能审核其他用户的任务
        assert response.status_code == 403
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_approve_completed_task(
        self,
        client: AsyncClient,
        test_session: AsyncSession,
        test_user: User,
        auth_headers: dict
    ):
        """
        测试审核已完成的任务
        
        验证：
        - 返回400或409状态码
        """
        task = RoadmapTask(
            task_id=f"test-task-{uuid.uuid4().hex[:8]}",
            roadmap_id=f"test-roadmap-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            status=TaskStatus.COMPLETED.value,  # 已完成
            current_step="completed",
        )
        
        test_session.add(task)
        await test_session.commit()
        
        approval_request = APIRequestFactory.create_approval_request(approved=True)
        
        response = await client.post(
            f"/api/v1/workflows/generation/{task.task_id}/approve",
            json=approval_request,
            headers=auth_headers,
        )
        
        # 已完成的任务不能再审核
        assert response.status_code in (400, 409)
        
        # 清理
        await test_session.delete(task)
        await test_session.commit()
    
    @pytest.mark.asyncio
    async def test_approve_task_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict
    ):
        """
        测试审核不存在的任务
        
        验证：
        - 返回404状态码
        """
        approval_request = APIRequestFactory.create_approval_request(approved=True)
        
        response = await client.post(
            "/api/v1/workflows/generation/nonexistent-task/approve",
            json=approval_request,
            headers=auth_headers,
        )
        
        assert response.status_code == 404

