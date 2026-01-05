"""
Celery 任务统一异常处理

提供 @safe_task 装饰器和相关工具函数，统一处理 Celery 任务中的异常。

注意：
- 现有任务使用 run_async 模式（同步任务包装异步代码），无需重构
- Celery 信号处理器（task_failure、task_retry）已注册，作为全局兜底机制
- 新任务可以选择使用 @safe_task 装饰器
"""
import functools
import traceback
from typing import Callable, Optional, Any
from celery import Task
import structlog

from app.config.settings import settings
from app.core.exceptions import sanitize_error_message

logger = structlog.get_logger()


async def update_task_status_failed(task_id: str, error: Exception) -> None:
    """
    更新任务状态为失败
    
    Args:
        task_id: 追踪 ID
        error: 异常对象
    """
    try:
        from app.db.session import AsyncSessionLocal
        from app.db.repositories.roadmap_repo import RoadmapRepository
        
        async with AsyncSessionLocal() as session:
            repo = RoadmapRepository(session)
            
            # 清理错误消息（移除敏感信息）
            error_message = sanitize_error_message(str(error), error)
            
            await repo.update_task_status(
                task_id=task_id,
                status="failed",
                current_step="failed",
                error_message=error_message[:500],  # 限制长度
            )
            await session.commit()
            
            logger.debug(
                "task_status_updated_to_failed",
                task_id=task_id,
            )
    except Exception as db_error:
        # 如果更新数据库失败，记录日志但不影响主异常
        logger.error(
            "failed_to_update_task_status",
            task_id=task_id,
            error=str(db_error),
            error_type=type(db_error).__name__,
        )


def should_retry(exception: Exception) -> bool:
    """
    判断异常是否应该重试
    
    某些临时性错误（如网络超时、数据库连接失败）应该重试，
    而业务逻辑错误（如数据验证失败）不应该重试。
    
    Args:
        exception: 异常对象
        
    Returns:
        bool: 是否应该重试
    """
    # 可重试的异常类型
    retryable_exceptions = (
        ConnectionError,
        TimeoutError,
        # 可以根据需要添加更多异常类型
    )
    
    return isinstance(exception, retryable_exceptions)


def exponential_backoff(retry_count: int, base_delay: int = 60) -> int:
    """
    指数退避策略
    
    计算重试延迟时间（秒）。
    
    Args:
        retry_count: 当前重试次数
        base_delay: 基础延迟时间（秒）
        
    Returns:
        int: 延迟时间（秒）
        
    Example:
        >>> exponential_backoff(0)  # 第 1 次重试
        60
        >>> exponential_backoff(1)  # 第 2 次重试
        120
        >>> exponential_backoff(2)  # 第 3 次重试
        240
    """
    return base_delay * (2 ** retry_count)


def safe_task(**celery_kwargs):
    """
    Celery 任务装饰器，自动处理异常
    
    功能：
    1. 统一的错误日志记录（使用 structlog）
    2. 自动更新任务状态为 failed
    3. 生产环境隐藏堆栈信息
    4. 支持任务重试逻辑（可选）
    
    使用方式：
        @safe_task(bind=True, max_retries=3)
        async def my_task(self, task_id: str, ...):
            # 任务逻辑
            ...
    
    Args:
        **celery_kwargs: 传递给 @celery_app.task() 的参数
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        from app.core.celery_app import celery_app
        
        # 创建 Celery 任务
        @celery_app.task(**celery_kwargs)
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 提取 task_id（支持多种传参方式）
            task_id = kwargs.get('task_id')
            if not task_id and args:
                # 尝试从第一个参数提取（常见模式：第一个参数是 request_dict，包含 task_id）
                if isinstance(args[0], dict):
                    task_id = args[0].get('task_id')
            
            # 如果仍然没有 task_id，使用 Celery 任务 ID
            if not task_id:
                task_id = wrapper.request.id
            
            try:
                # 执行原始任务
                result = await func(*args, **kwargs)
                
                logger.debug(
                    "celery_task_succeeded",
                    task_id=task_id,
                    task_name=func.__name__,
                )
                
                return result
                
            except Exception as e:
                # 记录结构化日志
                log_data = {
                    "task_id": task_id,
                    "task_name": func.__name__,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                
                # 仅在开发环境记录完整堆栈
                if settings.DEBUG or settings.ENVIRONMENT == "development":
                    log_data["traceback"] = traceback.format_exc()
                
                logger.error("celery_task_failed", **log_data)
                
                # 更新任务状态为失败
                await update_task_status_failed(task_id, e)
                
                # 决定是否重试
                if should_retry(e):
                    max_retries = celery_kwargs.get('max_retries', 3)
                    current_retries = wrapper.request.retries
                    
                    if current_retries < max_retries:
                        countdown = exponential_backoff(current_retries)
                        
                        logger.info(
                            "celery_task_retry",
                            task_id=task_id,
                            task_name=func.__name__,
                            retry_count=current_retries + 1,
                            max_retries=max_retries,
                            countdown=countdown,
                        )
                        
                        # 重新抛出异常，触发 Celery 重试
                        raise wrapper.retry(exc=e, countdown=countdown)
                
                # 不重试或已达到最大重试次数，重新抛出异常
                raise
        
        return wrapper
    
    return decorator


# ============================================================
# Celery 信号处理器（用于捕获未被 @safe_task 包装的任务）
# ============================================================

def handle_task_failure(sender: Optional[Task] = None, task_id: Optional[str] = None, 
                       exception: Optional[Exception] = None, **kwargs) -> None:
    """
    Celery 任务失败信号处理器
    
    捕获所有未被 @safe_task 装饰器处理的任务异常。
    
    Args:
        sender: 任务实例
        task_id: Celery 任务 ID
        exception: 异常对象
        **kwargs: 其他信号参数
    """
    task_name = sender.name if sender else "Unknown"
    
    log_data = {
        "task_id": task_id,
        "task_name": task_name,
        "error_type": type(exception).__name__ if exception else "Unknown",
        "error_message": str(exception) if exception else "No error message",
        "signal": "task_failure",
    }
    
    # 仅在开发环境记录完整堆栈
    if settings.DEBUG or settings.ENVIRONMENT == "development":
        if exception:
            log_data["traceback"] = "".join(
                traceback.format_exception(type(exception), exception, exception.__traceback__)
            )
    
    logger.error("celery_task_failure_signal", **log_data)


def handle_task_retry(sender: Optional[Task] = None, task_id: Optional[str] = None, **kwargs) -> None:
    """
    Celery 任务重试信号处理器
    
    记录任务重试事件。
    
    Args:
        sender: 任务实例
        task_id: Celery 任务 ID
        **kwargs: 其他信号参数（包含 reason、einfo 等）
    """
    task_name = sender.name if sender else "Unknown"
    reason = kwargs.get('reason', 'Unknown')
    
    logger.info(
        "celery_task_retry_signal",
        task_id=task_id,
        task_name=task_name,
        reason=str(reason),
        signal="task_retry",
    )

