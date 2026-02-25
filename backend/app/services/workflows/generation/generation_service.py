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
            # ✅ 不需要手动 commit，async_session_maker.begin() 自动处理
            
            logger.debug(
                "task_created_and_committed",
                task_id=task_id,
                user_id=user_request.user_id,
            )
        
        # 第二步：验证任务持久化（减少重试次数以提升响应速度）
        # ✅ 优化：从5次减少到2次，减少最坏情况延迟
        task_verified = await self._verify_task_persistence(
            task_id, max_retries=2
        )
        
        if not task_verified:
            logger.error(
                "task_persistence_verification_failed",
                task_id=task_id,
                max_retries=2,
            )
            raise ValueError(f"任务创建失败：数据库持久化验证失败（task_id={task_id}）")
        
        # 第三步：分发Celery任务
        # 使用 asyncio.to_thread 避免 .delay() 同步阻塞事件循环
        from app.tasks.roadmap_generation_tasks import generate_roadmap
        
        celery_task = await asyncio.to_thread(
            generate_roadmap.apply_async,
            kwargs={
                "task_id": task_id,
                "user_request": user_request.preferences.learning_goal,
                "user_id": user_request.user_id,
                "learning_preferences": user_request.preferences.model_dump(mode='json'),
            },
        )
        
        # 第四步：更新celery_task_id
        async with async_session_maker.begin() as session:
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)
            if task:
                task.celery_task_id = celery_task.id
                session.add(task)
                # ✅ 不需要手动 commit，async_session_maker.begin() 自动处理
        
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
                # ✅ 优化：减少等待时间 30ms, 60ms (原50ms, 100ms)
                await asyncio.sleep(0.03 * (attempt + 1))
        
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
        
        # 4. 通知 Celery 撤销任务
        # 策略：协作式取消（Cooperative Cancellation）
        # - 仅使用 revoke()（不带 terminate），阻止尚未被 worker 取走的任务执行
        # - 对于已在执行中的任务，依赖步骤5将状态写入数据库，
        #   workflow_execution_service 在节点间的检查点感知到 cancelled 状态后主动停止
        # 
        # 为什么不使用 terminate=True + SIGKILL：
        # - SIGKILL 通过 broker 广播，有延迟，不是立即执行
        # - acks_late=True 时：SIGKILL 杀死进程后任务消息尚未 ack，
        #   若 reject_on_worker_lost=True 则任务被重新放回队列，取消完全失效
        if task.celery_task_id:
            try:
                from celery.result import AsyncResult
                from app.core.celery_app import celery_app
                
                celery_result = AsyncResult(task.celery_task_id, app=celery_app)
                
                # revoke() 是 Celery 的同步阻塞调用，内部需要连接 Redis broker。
                # 问题：Redis 连接慢/超时时，即使用 run_in_executor 卸到线程，
                # await 仍会无限期等待线程返回，导致 cancel 请求永远不返回。
                #
                # 正确做法：用 asyncio.wait_for 加 3 秒硬超时。
                # - 超时后记录警告并跳过，继续执行数据库状态更新（才是真正的取消手段）
                # - revoke 仅是辅助性 broker 通知，用于阻止尚未被 worker 取走的排队任务
                # - 对于已在执行中的任务，协作式取消依赖数据库状态变更，不依赖 revoke
                loop = asyncio.get_event_loop()
                try:
                    await asyncio.wait_for(
                        loop.run_in_executor(None, celery_result.revoke),
                        timeout=3.0,
                    )
                    logger.info(
                        "celery_task_revoked",
                        task_id=task_id,
                        celery_task_id=task.celery_task_id,
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "celery_task_revoke_timeout",
                        task_id=task_id,
                        celery_task_id=task.celery_task_id,
                        message="revoke 超时（3s），跳过 broker 通知，依赖数据库状态取消",
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
            # ✅ 不需要手动 commit，async_session_maker.begin() 自动处理
        
        logger.info(
            "task_cancelled",
            task_id=task_id,
            previous_status=previous_status,
        )
        
        # 6. 发送WebSocket通知
        try:
            from app.services.shared.notification_service import notification_service
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
    
    async def delete_task(
        self,
        task_id: str,
        user_id: str,
    ) -> dict:
        """
        删除路线图生成任务
        
        执行步骤：
        1. 验证任务存在且属于当前用户
        2. 如果任务状态为 processing，先取消任务
        3. 删除任务记录
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            删除结果
            
        Raises:
            ValueError: 任务不存在
            PermissionError: 无权限删除此任务
        """
        # 1. 获取任务记录
        async with async_session_maker.begin() as session:
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)
        
        if not task:
            logger.warning("delete_task_not_found", task_id=task_id, user_id=user_id)
            raise ValueError("任务不存在")
        
        # 2. 验证用户权限
        if task.user_id != user_id:
            logger.warning(
                "delete_task_forbidden",
                task_id=task_id,
                task_user_id=task.user_id,
                current_user_id=user_id,
            )
            raise PermissionError("您没有权限删除此任务")
        
        # 3. 如果任务状态为 processing，先取消任务
        if task.status == "processing":
            logger.info(
                "delete_task_cancel_first",
                task_id=task_id,
                status=task.status,
            )
            try:
                # 先取消正在运行的任务
                await self.cancel_task(task_id, user_id)
                logger.info(
                    "delete_task_cancelled_before_delete",
                    task_id=task_id,
                )
            except Exception as e:
                logger.error(
                    "delete_task_cancel_failed",
                    task_id=task_id,
                    error=str(e),
                )
                # 即使取消失败，仍然继续删除流程
        
        previous_status = task.status
        
        # 4. 删除任务记录
        async with async_session_maker.begin() as session:
            task_crud = get_task_crud()
            # 重新获取任务（可能已被cancel更新）
            task = await task_crud.get_by_task_id(session, task_id)
            if task:
                await session.delete(task)
                # ✅ 不需要手动 commit，async_session_maker.begin() 自动处理
        
        logger.info(
            "task_deleted",
            task_id=task_id,
            previous_status=previous_status,
            user_id=user_id,
        )
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "任务已删除",
            "previous_status": previous_status,
        }


def get_generation_service() -> GenerationService:
    """
    获取GenerationService实例（依赖注入工厂）
    
    Returns:
        GenerationService实例
    """
    return GenerationService()

