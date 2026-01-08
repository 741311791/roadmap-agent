"""
路线图生成服务

将generate_roadmap_async的复杂业务逻辑封装到Service层，
实现任务创建、持久化验证、Celery调度等功能。
"""
import asyncio
import uuid
import structlog

from app.db.session import async_session_maker
from app.crud.crud_task import get_task_crud
from app.models.domain import UserRequest

logger = structlog.get_logger()


class GenerationService:
    """
    路线图生成服务
    
    负责处理路线图生成任务的创建、验证和调度。
    """
    
    async def create_and_verify_task(
        self,
        user_request: UserRequest,
    ) -> tuple[str, str]:
        """
        创建任务并验证持久化
        
        执行步骤：
        1. 创建任务记录并commit
        2. 验证任务已持久化（最多重试5次，指数退避）
        3. 分发Celery任务
        4. 更新celery_task_id
        
        Args:
            user_request: 用户请求
            
        Returns:
            (task_id, celery_task_id)
            
        Raises:
            ValueError: 任务创建失败或持久化验证失败
        """
        task_id = str(uuid.uuid4())
        
        logger.info(
            "generation_service_create_task",
            task_id=task_id,
            user_id=user_request.user_id,
            learning_goal=user_request.preferences.learning_goal,
        )
        
        # 第一步：创建任务记录
        async with async_session_maker.begin() as session:
            task_crud = get_task_crud()
            await task_crud.create(
                session,
                obj_in={
                    "task_id": task_id,
                    "user_id": user_request.user_id,
                    "user_request": user_request.model_dump(mode='json'),
                    "status": "pending",
                    "task_type": "creation",
                }
            )
            await session.commit()
            
            logger.debug(
                "task_created_and_committed",
                task_id=task_id,
                user_id=user_request.user_id,
            )
        
        # 第二步：验证任务持久化（最多重试5次）
        task_verified = await self._verify_task_persistence(
            task_id, max_retries=5
        )
        
        if not task_verified:
            logger.error(
                "task_persistence_verification_failed",
                task_id=task_id,
                max_retries=5,
            )
            raise ValueError(f"任务创建失败：数据库持久化验证失败（task_id={task_id}）")
        
        # 第三步：分发Celery任务
        from app.tasks.roadmap_generation_tasks import generate_roadmap
        
        celery_task = generate_roadmap.delay(
            task_id=task_id,
            user_request=user_request.preferences.learning_goal,
            user_id=user_request.user_id,
            learning_preferences=user_request.preferences.model_dump(mode='json'),
        )
        
        # 第四步：更新celery_task_id
        async with async_session_maker.begin() as session:
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)
            if task:
                task.celery_task_id = celery_task.id
                session.add(task)
                await session.commit()
        
        logger.info(
            "celery_task_dispatched",
            task_id=task_id,
            celery_task_id=celery_task.id,
        )
        
        return task_id, celery_task.id
    
    async def _verify_task_persistence(
        self,
        task_id: str,
        max_retries: int = 5,
    ) -> bool:
        """
        验证任务是否已持久化
        
        由于数据库连接池和事务隔离，刚commit的数据可能在另一个连接中不可见。
        使用独立session验证，确保在分发Celery任务前数据已完全可见。
        
        Args:
            task_id: 任务ID
            max_retries: 最大重试次数
            
        Returns:
            是否验证成功
        """
        for attempt in range(max_retries):
            async with async_session_maker.begin() as session:
                task_crud = get_task_crud()
                task = await task_crud.get_by_task_id(session, task_id)
                
                if task:
                    logger.debug(
                        "task_persistence_verified",
                        task_id=task_id,
                        attempt=attempt + 1,
                    )
                    return True
            
            if attempt < max_retries - 1:
                logger.warning(
                    "task_not_visible_retrying",
                    task_id=task_id,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                )
                # 指数退避等待：50ms, 100ms, 150ms, 200ms
                await asyncio.sleep(0.05 * (attempt + 1))
        
        return False
    
    async def cancel_task(
        self,
        task_id: str,
        user_id: str,
    ) -> dict:
        """
        取消路线图生成任务
        
        执行步骤：
        1. 验证任务存在且属于当前用户
        2. 检查任务状态（仅支持取消processing状态）
        3. 如果有celery_task_id，调用Celery revoke终止后台任务
        4. 更新数据库状态为cancelled
        5. 发送WebSocket通知
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            取消结果
            
        Raises:
            ValueError: 任务不存在、权限不足或状态不允许取消
        """
        # 1. 获取任务记录
        async with async_session_maker.begin() as session:
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)
        
        if not task:
            logger.warning("cancel_task_not_found", task_id=task_id, user_id=user_id)
            raise ValueError("任务不存在")
        
        # 2. 验证用户权限
        if task.user_id != user_id:
            logger.warning(
                "cancel_task_forbidden",
                task_id=task_id,
                task_user_id=task.user_id,
                current_user_id=user_id,
            )
            raise PermissionError("您没有权限取消此任务")
        
        # 3. 检查任务状态
        if task.status != "processing":
            logger.warning(
                "cancel_task_invalid_status",
                task_id=task_id,
                current_status=task.status,
            )
            raise ValueError(f"无法取消状态为 '{task.status}' 的任务，只能取消 'processing' 状态的任务")
        
        previous_status = task.status
        
        # 4. 终止Celery任务
        if task.celery_task_id:
            try:
                from celery.result import AsyncResult
                from app.core.celery_app import celery_app
                
                result = AsyncResult(task.celery_task_id, app=celery_app)
                result.revoke(terminate=True, signal='SIGKILL')
                
                logger.info(
                    "celery_task_revoked",
                    task_id=task_id,
                    celery_task_id=task.celery_task_id,
                )
            except Exception as e:
                logger.error(
                    "celery_task_revoke_failed",
                    task_id=task_id,
                    celery_task_id=task.celery_task_id,
                    error=str(e),
                )
        
        # 5. 更新数据库状态
        async with async_session_maker.begin() as session:
            task_crud = get_task_crud()
            await task_crud.update_task_status(
                session,
                task_id=task_id,
                status="cancelled",
                current_step=task.current_step,
                error_message="Task cancelled by user",
            )
            await session.commit()
        
        logger.info(
            "task_cancelled",
            task_id=task_id,
            previous_status=previous_status,
        )
        
        # 6. 发送WebSocket通知
        try:
            from app.services.notification_service import notification_service
            await notification_service.publish_failed(
                task_id=task_id,
                error="Task cancelled by user",
                step=task.current_step,
            )
        except Exception as e:
            logger.error(
                "cancel_notification_failed",
                task_id=task_id,
                error=str(e),
            )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已取消",
            "previous_status": previous_status,
        }


def get_generation_service() -> GenerationService:
    """
    获取GenerationService实例（依赖注入工厂）
    
    Returns:
        GenerationService实例
    """
    return GenerationService()

