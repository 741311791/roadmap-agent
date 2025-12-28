"""
日志任务 (Log Tasks)

Celery 任务：批量写入执行日志到数据库。

支持场景：
- 工作流节点日志（IntentAnalysis, CurriculumDesign, Validation, Editor, Review, Content 等）
- Agent 执行日志（开始、完成、错误）
- 工具调用日志
- 重试场景日志
- 错误处理日志

架构：
- FastAPI 应用：将日志放入本地缓冲区,批量发送到 Celery
- Celery Worker：独立进程，批量写入数据库
- 独立数据库连接池：不影响主应用连接池

事件循环策略：
- 每个 Worker 进程维护一个事件循环（不关闭）
- 通过 max_tasks_per_child 定期重启进程来清理资源
- 避免在任务结束时关闭循环导致的清理问题
"""
import structlog
import asyncio
from app.core.celery_app import celery_app
from app.db.session import safe_session
from app.models.database import ExecutionLog

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


@celery_app.task(
    name="app.tasks.log_tasks.batch_write_logs",
    queue="logs",
    max_retries=3,
    default_retry_delay=60,
    bind=True,
    ignore_result=True,  # 日志任务不需要存储结果，减少 Redis 操作和超时风险
)
def batch_write_logs(self, logs: list[dict]):
    """
    批量写入日志（Celery 任务）
    
    Args:
        logs: 日志数据列表，每个元素是一个字典，包含 ExecutionLog 的所有字段
    
    支持场景：
    - 工作流节点日志（IntentAnalysis, CurriculumDesign, Validation 等）
    - Agent 执行日志（开始、完成、错误）
    - 工具调用日志
    - 重试场景日志
    - 错误处理日志
    
    重试策略：
    - 最多重试 3 次
    - 每次重试间隔 60 秒
    - 使用指数退避策略
    
    事件循环处理：
    - 使用 Worker 进程级别的事件循环
    - 不在任务结束时关闭循环，避免连接清理问题
    - Worker 进程通过 max_tasks_per_child 定期重启来清理资源
    """
    if not logs:
        return
    
    try:
        # 获取 Worker 进程的事件循环
        loop = get_worker_loop()
        
        # 执行异步写入
        loop.run_until_complete(_async_batch_write_logs(logs))
        
        logger.debug(
            "celery_logs_batch_written",
            count=len(logs),
            task_ids=list(set(log.get("task_id") for log in logs if log.get("task_id"))),
        )
    except Exception as e:
        logger.error(
            "celery_logs_batch_write_failed",
            error=str(e),
            error_type=type(e).__name__,
            batch_size=len(logs),
        )
        # 重试整个批次
        raise self.retry(exc=e, countdown=60)


async def _async_batch_write_logs(logs: list[dict]):
    """
    异步批量写入日志（内部辅助函数）
    
    Args:
        logs: 日志数据列表
    
    注意：
    - 每次调用都会创建新的数据库会话
    - 会话在 safe_session 上下文管理器中自动管理
    - 不需要手动清理连接，safe_session 会处理
    """
    async with safe_session() as session:
        log_entries = [
            ExecutionLog(**log_data)
            for log_data in logs
        ]
        session.add_all(log_entries)
        await session.commit()


