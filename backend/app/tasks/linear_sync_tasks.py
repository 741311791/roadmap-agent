"""
Linear 产品路书同步 Celery 任务
"""
import structlog

from app.core.celery_app import celery_app
from app.db.celery_session import get_celery_session

logger = structlog.get_logger()


@celery_app.task(
    name="roadmap.sync_public",
    bind=True,
)
def sync_public_roadmap_task(self) -> dict:
    """
    同步公开产品路书快照
    """
    logger.info("public_roadmap_sync_task_started")

    try:
        from app.tasks.event_loop_manager import run_async_in_worker_loop

        result = run_async_in_worker_loop(_sync_public_roadmap_async())
        logger.info(
            "public_roadmap_sync_task_completed",
            milestone_count=result["milestone_count"],
            feature_count=result["feature_count"],
            upcoming_feature_count=result["upcoming_feature_count"],
        )
        return result
    except Exception as exc:
        logger.error(
            "public_roadmap_sync_task_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            exc_info=True,
        )
        return {
            "success": False,
            "error": str(exc),
        }


async def _sync_public_roadmap_async() -> dict:
    """
    执行产品路书同步
    """
    from app.services.roadmap.linear_sync_service import get_linear_sync_service

    async with get_celery_session() as session:
        result = await get_linear_sync_service().sync_all(session)
        return {
            "success": True,
            "milestone_count": result.milestone_count,
            "feature_count": result.feature_count,
            "upcoming_feature_count": result.upcoming_feature_count,
        }
