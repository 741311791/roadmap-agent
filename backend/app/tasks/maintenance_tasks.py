"""
系统维护 Celery 任务

包含定期清理和维护任务：
- cleanup_old_checkpoints: 清理旧的 Checkpoint 记录
- monitor_checkpoint_size: 监控 Checkpoint 表大小

LangGraph 1.0 最佳实践：
- Checkpoint 表会随着时间增长，需要定期清理
- 仅删除已完成任务的 Checkpoint（7 天前）
- 失败任务的 Checkpoint 保留更长时间（30 天）
"""
import structlog
from datetime import datetime, timedelta
from sqlalchemy import text

from app.core.celery_app import celery_app
from app.db.celery_session import get_celery_session

logger = structlog.get_logger()


@celery_app.task(
    name="maintenance.cleanup_old_checkpoints",
    bind=True,
)
def cleanup_old_checkpoints(self) -> dict:
    """
    清理旧的 Checkpoint 记录（Celery 任务）
    
    清理策略：
    - 已完成任务：保留 7 天
    - 失败任务：保留 30 天
    - 进行中任务：不清理
    
    Returns:
        dict: 清理结果统计
    """
    import asyncio
    
    logger.info("checkpoint_cleanup_started")
    
    try:
        # 在 Worker 进程的事件循环中执行异步清理
        result = asyncio.run(_cleanup_old_checkpoints_async())
        
        logger.info(
            "checkpoint_cleanup_completed",
            deleted_completed=result["deleted_completed"],
            deleted_failed=result["deleted_failed"],
            total_deleted=result["total_deleted"],
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "checkpoint_cleanup_failed",
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


async def _cleanup_old_checkpoints_async() -> dict:
    """
    清理旧的 Checkpoint 记录（异步）
    
    Returns:
        dict: 清理结果统计
    """
    # 计算截止时间
    completed_cutoff = datetime.utcnow() - timedelta(days=7)
    failed_cutoff = datetime.utcnow() - timedelta(days=30)
    
    logger.info(
        "checkpoint_cleanup_executing",
        completed_cutoff=completed_cutoff.isoformat(),
        failed_cutoff=failed_cutoff.isoformat(),
    )
    
    deleted_completed = 0
    deleted_failed = 0
    
    async with get_celery_session() as session:
        # 清理已完成任务的 Checkpoint（7 天前）
        # 注意：LangGraph Checkpoint 表名为 "checkpoints"
        # metadata 字段是 JSONB，包含任务状态信息
        result_completed = await session.execute(
            text("""
                DELETE FROM checkpoints
                WHERE thread_id IN (
                    SELECT task_id 
                    FROM roadmap_tasks 
                    WHERE status = 'completed' 
                      AND updated_at < :cutoff
                )
            """),
            {"cutoff": completed_cutoff}
        )
        deleted_completed = result_completed.rowcount
        
        # 清理失败任务的 Checkpoint（30 天前）
        result_failed = await session.execute(
            text("""
                DELETE FROM checkpoints
                WHERE thread_id IN (
                    SELECT task_id 
                    FROM roadmap_tasks 
                    WHERE status = 'failed' 
                      AND updated_at < :cutoff
                )
            """),
            {"cutoff": failed_cutoff}
        )
        deleted_failed = result_failed.rowcount
        
        await session.commit()
    
    total_deleted = deleted_completed + deleted_failed
    
    logger.info(
        "checkpoint_cleanup_summary",
        deleted_completed=deleted_completed,
        deleted_failed=deleted_failed,
        total_deleted=total_deleted,
    )
    
    return {
        "success": True,
        "deleted_completed": deleted_completed,
        "deleted_failed": deleted_failed,
        "total_deleted": total_deleted,
        "completed_cutoff": completed_cutoff.isoformat(),
        "failed_cutoff": failed_cutoff.isoformat(),
    }


@celery_app.task(
    name="maintenance.monitor_checkpoint_size",
    bind=True,
)
def monitor_checkpoint_size(self) -> dict:
    """
    监控 Checkpoint 表大小（Celery 任务）
    
    记录表大小和行数，用于性能分析和告警。
    
    Returns:
        dict: 监控结果
    """
    import asyncio
    
    logger.info("checkpoint_size_monitoring_started")
    
    try:
        result = asyncio.run(_monitor_checkpoint_size_async())
        
        logger.info(
            "checkpoint_size_monitoring_completed",
            total_rows=result["total_rows"],
            table_size_mb=result["table_size_mb"],
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "checkpoint_size_monitoring_failed",
            error=str(e),
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(e),
        }


async def _monitor_checkpoint_size_async() -> dict:
    """
    监控 Checkpoint 表大小（异步）
    
    Returns:
        dict: 监控结果
    """
    async with get_celery_session() as session:
        # 查询表大小
        result = await session.execute(
            text("""
                SELECT 
                    pg_size_pretty(pg_total_relation_size('checkpoints')) as table_size,
                    pg_total_relation_size('checkpoints') as table_size_bytes,
                    COUNT(*) as total_rows
                FROM checkpoints
            """)
        )
        row = result.fetchone()
        
        if row:
            table_size = row[0]
            table_size_bytes = row[1]
            total_rows = row[2]
            
            logger.info(
                "checkpoint_table_stats",
                table_size=table_size,
                table_size_bytes=table_size_bytes,
                table_size_mb=round(table_size_bytes / 1024 / 1024, 2),
                total_rows=total_rows,
            )
            
            # 如果表大小超过 5GB，记录警告
            if table_size_bytes > 5 * 1024 * 1024 * 1024:
                logger.warning(
                    "checkpoint_table_size_high",
                    table_size=table_size,
                    message="Checkpoint 表大小超过 5GB，建议增加清理频率",
                )
            
            return {
                "success": True,
                "total_rows": total_rows,
                "table_size": table_size,
                "table_size_bytes": table_size_bytes,
                "table_size_mb": round(table_size_bytes / 1024 / 1024, 2),
            }
        else:
            return {
                "success": False,
                "error": "Failed to query checkpoint table stats",
            }

