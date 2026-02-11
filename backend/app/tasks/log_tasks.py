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
"""
import structlog

from app.core.celery_app import celery_app
from app.tasks.utils import run_async
from app.db.celery_session import get_celery_session
from app.models.database import ExecutionLog

logger = structlog.get_logger()


@celery_app.task(
    name="app.tasks.log_tasks.batch_write_logs",
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
    
    重试策略：
    - 最多重试 3 次
    - 每次重试间隔 60 秒
    - 使用指数退避策略
    """
    if not logs:
        return
    
    try:
        # 执行异步写入
        run_async(_async_batch_write_logs(logs))
        
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
    - 会话由 get_celery_session() 自动管理
    - SQLAlchemy 自动处理 commit/rollback/close
    """
    async with get_celery_session() as session:
        log_entries = [
            ExecutionLog(**log_data)
            for log_data in logs
        ]
        session.add_all(log_entries)
        # ✅ 不需要手动 commit，get_celery_session() 自动处理


