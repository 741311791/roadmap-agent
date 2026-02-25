"""
路线图生成 Celery 任务

架构重构（v2.0）：
- 旧架构：Celery Task 层直接实现业务逻辑（重复代码严重）
- 新架构：业务逻辑集中在 WorkflowExecutionService，Task 层仅负责异步调度

职责边界：
- Service 层：业务逻辑编排、状态管理、数据持久化、通知发送
- Task 层：异步任务调度、事件循环管理

工作流阶段：
1. Intent Analysis（意图分析）
2. Curriculum Design（课程设计）
3. Structure Validation（结构验证，可能循环）
4. Human Review（人工审核，可选，会暂停）
5. Content Generation（内容生成）

架构优化（Celery Signal）：
- 使用 Celery Signal 实现事件驱动的封面图生成
- 路线图生成成功后自动触发封面图生成
- 完全解耦，符合关注点分离原则
"""
import structlog
from typing import Optional
from celery.signals import task_success

from app.core.celery_app import celery_app
from app.tasks.utils import run_async
from app.services.workflows.execution.workflow_execution_service import (
    get_workflow_execution_service,
)

logger = structlog.get_logger()


@celery_app.task(
    name="roadmap_generation.generate_roadmap",
    bind=True,
    acks_late=True,
    # ⚠️ 去掉 reject_on_worker_lost=True：
    # 原来的问题：revoke(terminate=True, signal='SIGKILL') 杀死进程后，
    # 由于 acks_late=True 任务未被 ack，reject_on_worker_lost 会将任务
    # 重新放回队列导致取消失效、任务重新执行。
    # 改为 False：进程意外死亡时任务消息被丢弃（不重新执行），
    # 正常业务崩溃由 mark_task_failed 兜底。
    reject_on_worker_lost=False,
    time_limit=1800,  # 30 分钟硬超时
    soft_time_limit=1680,  # 28 分钟软超时
)
def generate_roadmap(
    self,
    task_id: str,
    user_request: str,
    user_id: str,
    learning_preferences: Optional[dict] = None,
) -> dict:
    """
    生成路线图的 Celery 任务（简化版）
    
    架构重构：仅负责异步调度，业务逻辑在 WorkflowExecutionService。
    
    Args:
        task_id: 任务 ID
        user_request: 用户请求描述
        user_id: 用户 ID
        learning_preferences: 学习偏好（可选）
        
    Returns:
        dict: 执行结果
    """
    logger.info(
        "celery_task_started",
        task_id=task_id,
        celery_task_id=self.request.id,
        user_id=user_id,
    )
    
    try:
        workflow_service = get_workflow_execution_service()
        
        result = run_async(
            workflow_service.execute_roadmap_workflow(
                task_id=task_id,
                user_request=user_request,
                user_id=user_id,
                learning_preferences=learning_preferences,
                celery_task_id=self.request.id,
            )
        )
        
        logger.info(
            "celery_task_completed",
            task_id=task_id,
            success=result.get("success"),
            status=result.get("status"),
        )
        
        # 更新数据库中的任务最终状态
        run_async(workflow_service.update_task_final_status(task_id, result))
        
        return result
        
    except Exception as e:
        # ✅ 简化错误日志（不输出完整堆栈）
        from app.utils.log_formatters import truncate_string
        
        logger.error(
            "celery_task_failed",
            task_id=task_id,
            error=truncate_string(str(e), max_length=200),
            error_type=type(e).__name__,
        )
        
        # 标记任务为失败状态
        workflow_service = get_workflow_execution_service()
        run_async(workflow_service.mark_task_failed(task_id, str(e), exception=e))
        
        return {
            "success": False,
            "status": "failed",
            "error": truncate_string(str(e), max_length=200),
        }


# ============================================================
# Celery Signal 处理器：事件驱动的封面图生成
# ============================================================

@task_success.connect(sender=generate_roadmap)
def on_roadmap_generated(sender, result, **kwargs):
    """
    路线图生成成功后自动触发封面图生成
    
    架构优势（方案2 - Celery Signal）：
    - 完全解耦：路线图生成任务不关心封面图
    - 事件驱动：符合现代架构模式
    - 失败隔离：封面图生成失败不影响路线图创建
    - 易于扩展：可添加其他后处理任务（邮件通知、分享卡片等）
    
    Args:
        sender: 触发 Signal 的任务（generate_roadmap）
        result: 任务执行结果
        **kwargs: 其他 Signal 参数
            - task_id: Celery 任务 ID
            - args: 任务参数
            - kwargs: 任务关键字参数
    """
    # 仅在路线图生成成功时触发封面图生成
    if not result.get("success"):
        logger.debug(
            "skip_cover_image_generation_on_failure",
            result=result,
        )
        return
    
    roadmap_id = result.get("roadmap_id")
    if not roadmap_id:
        logger.warning(
            "skip_cover_image_generation_no_roadmap_id",
            result=result,
        )
        return
    
    # 从任务参数中提取 task_id（用于日志追踪）
    task_args = kwargs.get("args", [])
    task_id = task_args[0] if task_args else None
    
    # 使用路线图标题作为封面图生成提示词
    roadmap_title = result.get("roadmap_title")
    
    logger.info(
        "auto_trigger_cover_image_generation",
        roadmap_id=roadmap_id,
        roadmap_title=roadmap_title,
        task_id=task_id,
        trigger_source="celery_signal",
    )
    
    try:
        # 异步触发封面图生成任务
        from app.tasks.cover_image_tasks import generate_cover_image_task
        
        celery_task = generate_cover_image_task.delay(
            roadmap_id=roadmap_id,
            prompt=roadmap_title,
        )
        
        logger.info(
            "cover_image_task_dispatched",
            roadmap_id=roadmap_id,
            task_id=task_id,
            celery_task_id=celery_task.id,
            trigger_source="celery_signal",
        )
        
    except Exception as e:
        # 封面图生成失败不影响路线图（仅记录警告）
        logger.warning(
            "cover_image_task_dispatch_failed",
            roadmap_id=roadmap_id,
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )

