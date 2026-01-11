"""
路线图生成 Celery 任务

将完整的 LangGraph 工作流执行迁移到 Celery Worker，
实现所有 LLM 调用的异步处理。

架构变更：
- 旧架构：FastAPI 进程直接执行 LangGraph 工作流（阻塞）
- 新架构：FastAPI 分发任务 → Celery Worker 执行 LangGraph 工作流

工作流阶段：
1. Intent Analysis（意图分析）
2. Curriculum Design（课程设计）
3. Structure Validation（结构验证，可能循环）
4. Human Review（人工审核，可选，会暂停）
5. Content Generation（内容生成）

架构优化（方案2 - Celery Signal）：
- 使用 Celery Signal 实现事件驱动的封面图生成
- 路线图生成成功后自动触发封面图生成
- 完全解耦，符合关注点分离原则
"""
import asyncio
import structlog
from typing import Optional
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.orchestrator_factory import OrchestratorFactory
# 使用 Celery 专用的数据库连接管理，避免 Fork 进程继承问题
# CeleryRepositoryFactory 已删除，直接使用 CRUD
from app.services.shared.notification_service import notification_service
from app.models.constants import TaskStatus
from app.models.domain import UserRequest, LearningPreferences
from app.db.celery_session import get_celery_session
from app.crud.crud_task import get_task_crud
from celery.signals import task_success

logger = structlog.get_logger()

def run_async(coro):
    """
    在同步上下文中运行异步协程
    
    使用 asyncio.run() 确保每次执行都在干净的事件循环中进行，
    避免事件循环冲突和资源泄漏。
    
    asyncio.run() 会自动：
    1. 创建新的事件循环
    2. 设置为当前事件循环
    3. 运行协程
    4. 清理所有未完成的任务
    5. 关闭事件循环
    
    这是 Python 3.7+ 推荐的标准做法，避免手动管理事件循环。
    
    Args:
        coro: 异步协程对象
        
    Returns:
        协程的返回值
    """
    return asyncio.run(coro)


@celery_app.task(
    name="roadmap_generation.generate_roadmap",
    bind=True,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=1800,  # 30 分钟硬超时（路线图生成工作流包含多个阶段和 LLM 调用）
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
    生成路线图的 Celery 任务
    
    执行完整的 LangGraph 工作流，包括：
    - Intent Analysis
    - Curriculum Design
    - Structure Validation（循环）
    - Human Review（可选，会暂停工作流）
    - Content Generation
    
    Args:
        task_id: 任务 ID
        user_request: 用户请求描述
        user_id: 用户 ID
        learning_preferences: 学习偏好（可选）
        
    Returns:
        dict: 执行结果
            - success: bool
            - roadmap_id: str（如果成功）
            - status: str（任务最终状态）
            - error: str（如果失败）
    """
    logger.info(
        "celery_task_started",
        task_id=task_id,
        celery_task_id=self.request.id,
        user_id=user_id,
    )
    
    try:
        # 在 Worker 进程的事件循环中执行异步工作流
        result = run_async(
            _execute_roadmap_workflow(
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
        
        # 关键修复：Celery 任务完成后，更新数据库中的任务状态
        # 这样前端就不需要持续轮询，可以通过单次查询获取最终状态
        run_async(_update_task_final_status(task_id, result))
        
        return result
        
    except Exception as e:
        logger.error(
            "celery_task_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        
        # 更新任务状态为失败（传递异常对象以获取完整堆栈）
        run_async(_mark_task_failed(task_id, str(e), exception=e))
        
        return {
            "success": False,
            "status": "failed",
            "error": str(e),
        }


async def _execute_roadmap_workflow(
    task_id: str,
    user_request: str,
    user_id: str,
    learning_preferences: Optional[dict],
    celery_task_id: str,
) -> dict:
    """
    执行路线图生成工作流（异步）
    
    Args:
        task_id: 任务 ID
        user_request: 用户请求
        user_id: 用户 ID
        learning_preferences: 学习偏好
        celery_task_id: Celery 任务 ID
        
    Returns:
        dict: 执行结果
    """
    factory = None
    
    try:
        # 验证任务记录是否存在（直接查询，不重试）
        task_crud = get_task_crud()
        async with get_celery_session() as session:
            task = await task_crud.get_by_task_id(session, task_id)
            if not task:
                error_msg = f"Task {task_id} not found in database"
                logger.error("task_not_found", task_id=task_id)
                raise ValueError(error_msg)
            
            logger.info(
                "task_record_found",
                task_id=task_id,
                task_status=task.status,
            )
        
        # 更新任务状态为 processing
        task_crud = get_task_crud()
        async with get_celery_session() as session:
            await task_crud.update_task_status(
                session=session,
                task_id=task_id,
                status=TaskStatus.PROCESSING.value,
                current_step="queued",
            )
            await session.commit()
        
        # 发送 WebSocket 通知
        await notification_service.publish_progress(
            task_id=task_id,
            step="queued",
            status=TaskStatus.PROCESSING.value,
        )
        
        # 创建 Orchestrator Factory
        factory = OrchestratorFactory()
        await factory.initialize()
        
        # 创建工作流执行器
        executor = factory.create_workflow_executor()
        
        # 构造 UserRequest 对象
        user_request_obj = UserRequest(
            user_id=user_id,
            session_id=task_id,  # 使用 task_id 作为 session_id
            preferences=LearningPreferences(**learning_preferences) if learning_preferences else LearningPreferences(
                learning_goal=user_request,
                available_hours_per_week=10,
                motivation="Personal interest",
                current_level="beginner",
                career_background="Not specified",
            ),
            additional_context=user_request,
        )
        
        # 执行工作流（会在 human_review 处暂停）
        final_state = await executor.execute(
            user_request=user_request_obj,
            task_id=task_id,
        )
        
        # 检查最终状态
        roadmap_id = final_state.get("roadmap_id")
        current_step = final_state.get("current_step", "completed")
        
        # 判断任务状态
        if current_step == "human_review":
            # 工作流在人工审核处暂停
            status = TaskStatus.HUMAN_REVIEW
            success = True
            logger.info(
                "workflow_paused_for_review",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
        elif current_step == "completed":
            # 工作流完成
            status = TaskStatus.COMPLETED
            success = True
            logger.info(
                "workflow_completed",
                task_id=task_id,
                roadmap_id=roadmap_id,
            )
        else:
            # 其他情况视为部分完成
            status = TaskStatus.PARTIAL_FAILURE
            success = False
            logger.warning(
                "workflow_incomplete",
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
            "workflow_execution_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        raise
        
    finally:
        # 清理 Orchestrator Factory
        if factory:
            await factory.cleanup()


async def _update_task_final_status(
    task_id: str,
    result: dict,
):
    """
    更新任务最终状态（完成或部分失败）
    
    关键修复：Celery 任务执行完成后，必须更新数据库中的任务状态，
    否则前端会持续轮询状态而无法获取最终结果。
    
    Args:
        task_id: 任务 ID
        result: 执行结果字典
    """
    try:
        task_crud = get_task_crud()
        async with get_celery_session() as session:
            # 更新任务状态和 roadmap_id
            task = await task_crud.get_by_task_id(session, task_id)
            if task:
                task.status = result.get("status", TaskStatus.COMPLETED.value)
                task.current_step = result.get("current_step", "completed")
                task.roadmap_id = result.get("roadmap_id")
                session.add(task)
                await session.commit()
                
                logger.info(
                    "task_final_status_updated",
                    task_id=task_id,
                    status=task.status,
                    roadmap_id=task.roadmap_id,
                )
            else:
                logger.error(
                    "task_not_found_for_status_update",
                    task_id=task_id,
                )
    except Exception as e:
        logger.error(
            "failed_to_update_task_final_status",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )


async def _mark_task_failed(
    task_id: str,
    error_message: str,
    exception: Exception | None = None,
):
    """
    标记任务为失败状态
    
    Args:
        task_id: 任务 ID
        error_message: 错误信息
        exception: 原始异常对象（可选，用于提取堆栈跟踪）
    """
    try:
        # 使用 Celery 专用的数据库连接
        task_crud = get_task_crud()
        async with get_celery_session() as session:
            await task_crud.update_task_status(
                session=session,
                task_id=task_id,
                status=TaskStatus.FAILED.value,
                current_step="failed",
                error_message=error_message,
            )
            await session.commit()
        
        # 发送 WebSocket 通知（传递异常对象以获取完整堆栈）
        await notification_service.publish_failed(
            task_id=task_id,
            error=error_message,
            step="failed",
            exception=exception,
        )
        
    except Exception as e:
        logger.error(
            "failed_to_mark_task_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )


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
    
    logger.info(
        "auto_trigger_cover_image_generation",
        roadmap_id=roadmap_id,
        task_id=task_id,
        trigger_source="celery_signal",
    )
    
    try:
        # 异步触发封面图生成任务
        from app.tasks.cover_image_tasks import generate_cover_image_task
        
        celery_task = generate_cover_image_task.delay(
            roadmap_id=roadmap_id,
            prompt=None,  # 使用默认提示词（CoverImageService 会从路线图标题生成）
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

