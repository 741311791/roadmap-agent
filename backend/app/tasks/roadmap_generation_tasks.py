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
"""
import asyncio
import structlog
from typing import Optional
from datetime import datetime

from app.core.celery_app import celery_app
from app.core.orchestrator_factory import OrchestratorFactory
from app.db.repository_factory import RepositoryFactory
from app.services.notification_service import notification_service
from app.models.constants import TaskStatus
from app.models.domain import UserRequest, LearningPreferences

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
    name="roadmap_generation.generate_roadmap",
    bind=True,
    max_retries=0,  # 不自动重试，由用户手动触发重试
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
        
        return result
        
    except Exception as e:
        logger.error(
            "celery_task_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )
        
        # 更新任务状态为失败
        run_async(_mark_task_failed(task_id, str(e)))
        
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
        # 更新任务状态为 processing
        repo_factory = RepositoryFactory()
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status=TaskStatus.PROCESSING.value,
                current_step="queued",
            )
        
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


async def _mark_task_failed(task_id: str, error_message: str):
    """
    标记任务为失败状态
    
    Args:
        task_id: 任务 ID
        error_message: 错误信息
    """
    try:
        repo_factory = RepositoryFactory()
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status=TaskStatus.FAILED.value,
                current_step="failed",
                error_message=error_message,
            )
        
        # 发送 WebSocket 通知
        await notification_service.publish_failed(
            task_id=task_id,
            error=error_message,
            step="failed",
        )
        
    except Exception as e:
        logger.error(
            "failed_to_mark_task_failed",
            task_id=task_id,
            error=str(e),
            exc_info=True,
        )

