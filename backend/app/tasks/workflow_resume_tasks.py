"""
工作流恢复 Celery 任务

实现从 checkpoint 恢复工作流的 Celery 任务，支持：
1. Human Review 后恢复（用户批准/拒绝后继续）
2. 失败任务从 checkpoint 恢复（断点续传）

使用场景：
- resume_after_review: 用户完成人工审核后，恢复工作流继续执行
- resume_from_checkpoint: 任务失败后，从最后一个 checkpoint 恢复执行
"""
import asyncio
import structlog
from typing import Optional
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.orchestrator_factory import OrchestratorFactory
# 使用 Celery 专用的数据库连接管理，避免 Fork 进程继承问题
from app.db.celery_session import CeleryRepositoryFactory
from app.services.notification_service import notification_service
from app.models.constants import TaskStatus

logger = structlog.get_logger()

# 每个 Worker 进程的事件循环（懒加载）
_worker_loop = None


def get_worker_loop():
    """
    获取或创建 Worker 进程的事件循环
    
    每个 Worker 进程维护一个独立的事件循环，
    不在任务结束时关闭，避免连接清理问题。
    
    Returns:
        asyncio.AbstractEventLoop: Worker 进程的事件循环
    """
    global _worker_loop
    
    if _worker_loop is None or _worker_loop.is_closed():
        # 创建新的事件循环
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
        logger.debug("celery_worker_loop_created", loop_id=id(_worker_loop))
    
    return _worker_loop


def run_async(coro):
    """
    在同步上下文中运行异步协程
    
    使用 Worker 进程级别的事件循环，避免频繁创建/销毁循环。
    
    Args:
        coro: 异步协程对象
        
    Returns:
        协程的返回值
    """
    loop = get_worker_loop()
    return loop.run_until_complete(coro)


@celery_app.task(
    name="workflow_resume.resume_after_review",
    bind=True,
    max_retries=0,
    acks_late=True,
    reject_on_worker_lost=True,
)
def resume_after_review(
    self,
    task_id: str,
    approved: bool,
    feedback: Optional[str] = None,
) -> dict:
    """
    人工审核后恢复工作流的 Celery 任务
    
    从 checkpoint 恢复工作流，根据用户审核结果继续执行：
    - approved=True: 进入内容生成
    - approved=False: 进入修改流程（edit_plan_analysis → roadmap_edit → human_review）
    
    Args:
        task_id: 任务 ID
        approved: 用户是否批准
        feedback: 用户反馈（拒绝时提供）
        
    Returns:
        dict: 执行结果
            - success: bool
            - status: str（任务最终状态）
            - error: str（如果失败）
    """
    logger.info(
        "resume_after_review_started",
        task_id=task_id,
        celery_task_id=self.request.id,
        approved=approved,
    )
    
    try:
        # 在 Worker 进程的事件循环中执行异步恢复
        result = run_async(
            _resume_workflow_after_review(
                task_id=task_id,
                approved=approved,
                feedback=feedback,
                celery_task_id=self.request.id,
            )
        )
        
        logger.info(
            "resume_after_review_completed",
            task_id=task_id,
            success=result.get("success"),
            status=result.get("status"),
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "resume_after_review_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        
        # 更新任务状态为失败（捕获可能的事件循环冲突）
        try:
            run_async(_mark_task_failed(task_id, str(e)))
        except Exception as mark_error:
            logger.error(
                "failed_to_mark_task_as_failed",
                task_id=task_id,
                original_error=str(e),
                mark_error=str(mark_error),
                exc_info=True,
            )
        
        return {
            "success": False,
            "status": "failed",
            "error": str(e),
        }


@celery_app.task(
    name="workflow_resume.resume_from_checkpoint",
    bind=True,
    max_retries=0,
    acks_late=True,
    reject_on_worker_lost=True,
)
def resume_from_checkpoint(
    self,
    task_id: str,
) -> dict:
    """
    从 checkpoint 恢复失败任务的 Celery 任务
    
    用于重试失败的任务，从最后一个 checkpoint 恢复执行。
    适用于早期阶段失败（Intent、Curriculum、Validation）。
    
    Args:
        task_id: 任务 ID
        
    Returns:
        dict: 执行结果
            - success: bool
            - status: str（任务最终状态）
            - error: str（如果失败）
    """
    logger.info(
        "resume_from_checkpoint_started",
        task_id=task_id,
        celery_task_id=self.request.id,
    )
    
    try:
        # 在 Worker 进程的事件循环中执行异步恢复
        result = run_async(
            _resume_workflow_from_checkpoint(
                task_id=task_id,
                celery_task_id=self.request.id,
            )
        )
        
        logger.info(
            "resume_from_checkpoint_completed",
            task_id=task_id,
            success=result.get("success"),
            status=result.get("status"),
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "resume_from_checkpoint_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        
        # 更新任务状态为失败（捕获可能的事件循环冲突）
        try:
            run_async(_mark_task_failed(task_id, str(e)))
        except Exception as mark_error:
            logger.error(
                "failed_to_mark_task_as_failed",
                task_id=task_id,
                original_error=str(e),
                mark_error=str(mark_error),
                exc_info=True,
            )
        
        return {
            "success": False,
            "status": "failed",
            "error": str(e),
        }


async def _resume_workflow_after_review(
    task_id: str,
    approved: bool,
    feedback: Optional[str],
    celery_task_id: str,
) -> dict:
    """
    人工审核后恢复工作流（异步）
    
    Args:
        task_id: 任务 ID
        approved: 用户是否批准
        feedback: 用户反馈
        celery_task_id: Celery 任务 ID
        
    Returns:
        dict: 执行结果
    """
    factory = None
    
    try:
        # 更新任务状态为 processing
        repo_factory = CeleryRepositoryFactory()
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status=TaskStatus.PROCESSING.value,
                current_step="resuming",
            )
        
        # 发送 WebSocket 通知
        await notification_service.publish_progress(
            task_id=task_id,
            step="resuming",
            status=TaskStatus.PROCESSING.value,
            message="Resuming workflow after review...",
        )
        
        # 创建 Orchestrator Factory
        factory = OrchestratorFactory()
        await factory.initialize()
        
        # 创建工作流执行器
        executor = factory.create_workflow_executor()
        
        # 从 checkpoint 恢复工作流（人工审核后）
        final_state = await executor.resume_after_human_review(
            task_id=task_id,
            approved=approved,
            feedback=feedback,
        )
        
        # 检查最终状态
        roadmap_id = final_state.get("roadmap_id")
        current_step = final_state.get("current_step", "completed")
        
        # 判断任务状态
        if current_step == "human_review":
            # 用户拒绝后，工作流再次暂停在人工审核
            status = TaskStatus.HUMAN_REVIEW
            success = True
            logger.info(
                "workflow_paused_for_review_again",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
        elif current_step == "completed":
            # 工作流完成
            status = TaskStatus.COMPLETED
            success = True
            logger.info(
                "workflow_completed_after_review",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
        else:
            # 其他情况视为部分完成
            status = TaskStatus.PARTIAL_FAILURE
            success = False
            logger.warning(
                "workflow_incomplete_after_review",
                task_id=task_id,
                current_step=current_step,
            )
        
        return {
            "success": success,
            "roadmap_id": roadmap_id,
            "status": status.value,
            "current_step": current_step,
        }
        
    except Exception as e:
        logger.error(
            "resume_after_review_execution_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        raise
        
    finally:
        # 清理 Orchestrator Factory
        if factory:
            await factory.cleanup()


async def _resume_workflow_from_checkpoint(
    task_id: str,
    celery_task_id: str,
) -> dict:
    """
    从 checkpoint 恢复工作流（异步）
    
    Args:
        task_id: 任务 ID
        celery_task_id: Celery 任务 ID
        
    Returns:
        dict: 执行结果
    """
    factory = None
    
    try:
        # 更新任务状态为 processing
        repo_factory = CeleryRepositoryFactory()
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status=TaskStatus.PROCESSING.value,
                current_step="resuming",
            )
        
        # 发送 WebSocket 通知
        await notification_service.publish_progress(
            task_id=task_id,
            step="resuming",
            status=TaskStatus.PROCESSING.value,
            message="Resuming workflow from checkpoint...",
        )
        
        # 创建 Orchestrator Factory
        factory = OrchestratorFactory()
        await factory.initialize()
        
        # 创建工作流执行器
        executor = factory.create_workflow_executor()
        
        # 从 checkpoint 恢复工作流
        # LangGraph 配置（使用相同的 thread_id 会自动从 checkpoint 恢复）
        config = {"configurable": {"thread_id": task_id}}
        
        # 直接调用 graph.ainvoke，不传入初始状态（从 checkpoint 恢复）
        final_state = await executor.graph.ainvoke(None, config=config)
        
        # 检查最终状态
        roadmap_id = final_state.get("roadmap_id")
        current_step = final_state.get("current_step", "completed")
        
        # 判断任务状态
        if current_step == "human_review":
            # 工作流在人工审核处暂停
            status = TaskStatus.HUMAN_REVIEW
            success = True
            logger.info(
                "workflow_paused_for_review_from_checkpoint",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
        elif current_step == "completed":
            # 工作流完成
            status = TaskStatus.COMPLETED
            success = True
            logger.info(
                "workflow_completed_from_checkpoint",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
        else:
            # 其他情况视为部分完成
            status = TaskStatus.PARTIAL_FAILURE
            success = False
            logger.warning(
                "workflow_incomplete_from_checkpoint",
                task_id=task_id,
                current_step=current_step,
            )
        
        return {
            "success": success,
            "roadmap_id": roadmap_id,
            "status": status.value,
            "current_step": current_step,
        }
        
    except Exception as e:
        logger.error(
            "resume_from_checkpoint_execution_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        raise
        
    finally:
        # 清理 Orchestrator Factory
        if factory:
            await factory.cleanup()


async def _mark_task_failed(task_id: str, error_message: str):
    """
    标记任务为失败状态
    
    在异常处理上下文中调用，必须确保不会因为事件循环问题而失败。
    
    Args:
        task_id: 任务 ID
        error_message: 错误信息
    """
    # 1. 先更新数据库状态（关键操作）
    try:
        repo_factory = CeleryRepositoryFactory()
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status=TaskStatus.FAILED.value,
                current_step="failed",
                error_message=error_message,
            )
        logger.info(
            "task_marked_as_failed",
            task_id=task_id,
            error=error_message[:100],
        )
    except Exception as e:
        logger.error(
            "failed_to_update_task_status",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
    
    # 2. 尝试发送 WebSocket 通知（非关键操作，失败不影响状态更新）
    try:
        await notification_service.publish_failed(
            task_id=task_id,
            error=error_message,
            step="failed",
        )
    except Exception as e:
        # 在异常处理上下文中，通知失败是可以接受的
        # 仅记录警告，不抛出异常
        logger.warning(
            "failed_to_send_failure_notification",
            task_id=task_id,
            notification_error=str(e),
        )

