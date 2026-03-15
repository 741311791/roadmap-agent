"""
路线图生成服务

将generate_roadmap_async的复杂业务逻辑封装到Service层，
实现任务创建、持久化验证、Celery调度等功能。
"""
import asyncio
import uuid

import structlog

from app.models.constants import TaskStatus, WorkflowStep
from app.db.session import async_session_maker
from app.crud.crud_task import get_task_crud
from app.models.domain import UserRequest
from app.services.shared.notification_service import notification_service

logger = structlog.get_logger()
DISPATCH_TIMEOUT_SECONDS = 10.0


class GenerationService:
    """
    路线图生成服务
    
    负责处理路线图生成任务的创建、验证和调度。
    """
    
    async def create_and_verify_task(
        self,
        user_request: UserRequest,
    ) -> str:
        """
        创建任务并验证持久化
        
        执行步骤：
        1. 创建任务记录并commit
        2. 验证任务已持久化（最多重试5次，指数退避）
        3. 异步分发Celery任务（不阻塞HTTP响应）
        4. 后台更新celery_task_id
        
        Args:
            user_request: 用户请求
            
        Returns:
            task_id
            
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
                    "status": TaskStatus.PENDING.value,
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
        
        # 第三步：在后台分发 Celery 任务，避免用户等待 broker 响应。
        # 如果后台分发失败，任务仍保持 pending，启动时恢复机制会兜底重新入队。
        asyncio.create_task(
            self._dispatch_task_in_background(
                task_id=task_id,
                user_request=user_request,
            ),
            name=f"dispatch_roadmap_generation_{task_id}",
        )
        
        logger.info(
            "roadmap_generation_dispatch_scheduled",
            task_id=task_id,
        )
        
        return task_id

    async def _dispatch_task_in_background(
        self,
        task_id: str,
        user_request: UserRequest,
    ) -> None:
        """
        后台分发路线图生成 Celery 任务。

        设计目标：
        1. 将 broker 分发耗时从 HTTP 请求链路中移除
        2. 分发成功后异步写回 celery_task_id
        3. 分发失败时保留 pending 任务，交由恢复机制处理

        Args:
            task_id: 任务 ID
            user_request: 用户请求
        """
        try:
            from app.tasks.roadmap_generation_tasks import generate_roadmap

            logger.info(
                "celery_task_dispatch_started",
                task_id=task_id,
                user_id=user_request.user_id,
                timeout_seconds=DISPATCH_TIMEOUT_SECONDS,
            )

            celery_task = await asyncio.wait_for(
                asyncio.to_thread(
                    generate_roadmap.apply_async,
                    kwargs={
                        "task_id": task_id,
                        "user_request": user_request.preferences.learning_goal,
                        "user_id": user_request.user_id,
                        "learning_preferences": user_request.preferences.model_dump(mode="json"),
                        "turbo_mode": user_request.turbo_mode,
                    },
                ),
                timeout=DISPATCH_TIMEOUT_SECONDS,
            )

            async with async_session_maker.begin() as session:
                task_crud = get_task_crud()
                await task_crud.update_celery_id(
                    session=session,
                    task_id=task_id,
                    celery_task_id=celery_task.id,
                )

            logger.info(
                "celery_task_dispatched",
                task_id=task_id,
                celery_task_id=celery_task.id,
            )
        except asyncio.TimeoutError as exc:
            await asyncio.shield(
                self._mark_dispatch_failed(
                    task_id=task_id,
                    user_request=user_request,
                    error_message=(
                        f"Celery 任务派发超时（>{DISPATCH_TIMEOUT_SECONDS:.0f}秒），"
                        "任务已标记为失败，请手动重试"
                    ),
                    error=exc,
                    failure_reason="timeout",
                )
            )
        except asyncio.CancelledError as exc:
            await asyncio.shield(
                self._mark_dispatch_failed(
                    task_id=task_id,
                    user_request=user_request,
                    error_message="Celery 任务后台派发被取消，任务已标记为失败，请手动重试",
                    error=exc,
                    failure_reason="cancelled",
                )
            )
        except Exception as e:
            await self._mark_dispatch_failed(
                task_id=task_id,
                user_request=user_request,
                error_message=f"Celery 任务派发失败：{str(e)}",
                error=e,
                failure_reason="exception",
            )

    async def _mark_dispatch_failed(
        self,
        task_id: str,
        user_request: UserRequest,
        error_message: str,
        error: BaseException | None,
        failure_reason: str,
    ) -> None:
        """
        将后台派发失败明确落库，避免任务长期静默停留在 pending。

        Args:
            task_id: 任务 ID
            user_request: 用户请求
            error_message: 面向数据库和前端展示的错误信息
            error: 原始异常对象
            failure_reason: 失败分类（timeout/cancelled/exception）
        """
        logger.error(
            "celery_task_dispatch_failed",
            task_id=task_id,
            user_id=user_request.user_id,
            failure_reason=failure_reason,
            error=repr(error) if error else error_message,
            error_type=type(error).__name__ if error else None,
        )

        async with async_session_maker.begin() as session:
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)

            if not task:
                logger.warning(
                    "dispatch_failure_task_not_found",
                    task_id=task_id,
                    failure_reason=failure_reason,
                )
                return

            # Why：
            # 超时后的 to_thread 可能仍在后台继续执行，若此时 celery_task_id 已被其他链路写回，
            # 说明任务实际上已经完成入队，不应再覆盖为 failed。
            if task.celery_task_id:
                logger.warning(
                    "dispatch_failure_state_update_skipped",
                    task_id=task_id,
                    celery_task_id=task.celery_task_id,
                    current_status=task.status,
                    failure_reason=failure_reason,
                )
                return

            await task_crud.update_task_status(
                session=session,
                task_id=task_id,
                status=TaskStatus.FAILED.value,
                current_step=WorkflowStep.FAILED.value,
                error_message=error_message,
            )

        try:
            await notification_service.publish_failed(
                task_id=task_id,
                error=error_message,
                step=WorkflowStep.FAILED.value,
                exception=error if isinstance(error, Exception) else None,
            )
        except Exception as notification_error:
            logger.warning(
                "dispatch_failure_notification_failed",
                task_id=task_id,
                failure_reason=failure_reason,
                error=str(notification_error),
                error_type=type(notification_error).__name__,
            )
    
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
            if task.content_generation_status == "processing":
                await task_crud.update_content_generation_status(
                    session=session,
                    task_id=task_id,
                    status="failed",
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

