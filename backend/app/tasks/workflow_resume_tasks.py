"""
工作流恢复 Celery 任务

架构重构（v2.0）：
- 旧架构：Celery Task 层直接实现业务逻辑（重复代码严重）
- 新架构：业务逻辑集中在 WorkflowExecutionService，Task 层仅负责异步调度

职责边界：
- Service 层：业务逻辑编排、状态管理、数据持久化、通知发送
- Task 层：异步任务调度、事件循环管理

支持场景：
1. Human Review 后恢复（用户批准/拒绝后继续）
2. 失败任务从 checkpoint 恢复（断点续传）
"""
import structlog
from typing import Optional

from app.core.celery_app import celery_app
from app.tasks.utils import run_async
from app.services.workflows.execution.workflow_execution_service import (
    get_workflow_execution_service,
)

logger = structlog.get_logger()


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
    人工审核后恢复工作流的 Celery 任务（简化版）
    
    架构重构：仅负责异步调度，业务逻辑在 WorkflowExecutionService。
    
    Args:
        task_id: 任务 ID
        approved: 用户是否批准
        feedback: 用户反馈（拒绝时提供）
        
    Returns:
        dict: 执行结果
    """
    logger.info(
        "resume_after_review_started",
        task_id=task_id,
        celery_task_id=self.request.id,
        approved=approved,
    )
    
    try:
        # ✅ 调用 Service 层
        workflow_service = get_workflow_execution_service()
        
        result = run_async(
            workflow_service.resume_workflow_after_review(
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
        
        # 标记任务为失败
        workflow_service = get_workflow_execution_service()
        try:
            run_async(workflow_service.mark_task_failed(task_id, str(e), exception=e))
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
    checkpoint_id: Optional[str] = None,
) -> dict:
    """
    从 checkpoint 恢复失败任务的 Celery 任务（简化版）
    
    架构重构：仅负责异步调度，业务逻辑在 WorkflowExecutionService。
    
    支持两种模式：
    1. 断点续传（checkpoint_id=None）：从最后一个checkpoint恢复
    2. 时间旅行（checkpoint_id指定）：从特定checkpoint恢复
    
    Args:
        task_id: 任务 ID
        checkpoint_id: 可选的checkpoint ID（用于时间旅行）
        
    Returns:
        dict: 执行结果
    """
    logger.info(
        "resume_from_checkpoint_started",
        task_id=task_id,
        checkpoint_id=checkpoint_id,
        mode="time_travel" if checkpoint_id else "resume",
        celery_task_id=self.request.id,
    )
    
    try:
        # ✅ 调用 Service 层
        workflow_service = get_workflow_execution_service()
        
        result = run_async(
            workflow_service.resume_workflow_from_checkpoint(
                task_id=task_id,
                celery_task_id=self.request.id,
                checkpoint_id=checkpoint_id,
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
        
        # 标记任务为失败
        workflow_service = get_workflow_execution_service()
        try:
            run_async(workflow_service.mark_task_failed(task_id, str(e), exception=e))
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

