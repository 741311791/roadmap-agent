"""
陈旧 pending 任务清理服务

负责清理长时间停留在 init 的 pending 创建任务，避免历史孤儿任务长期污染
任务列表与详情页中的排队提示。
"""

from pydantic import BaseModel, Field
import structlog

from app.config.settings import settings
from app.crud.crud_task import get_task_crud
from app.db.session import async_session_maker

logger = structlog.get_logger()


class StalePendingTaskCleanupReport(BaseModel):
    """
    陈旧 pending 任务清理报告
    """

    total_found: int = Field(0, description="发现的候选任务数")
    cleaned: int = Field(0, description="成功清理的任务数")
    failed: int = Field(0, description="清理失败的任务数")
    task_ids: list[str] = Field(default_factory=list, description="涉及的任务 ID 列表")


class StalePendingTaskCleanupService:
    """
    陈旧 pending 任务清理服务

    设计原则：
    - 仅处理 task_type=creation、status=pending、current_step=init 的任务；
    - 仅处理超过阈值仍未启动的任务，避免误伤短暂排队中的正常请求；
    - 清理时保留任务记录，将其标记为 failed，便于后续追踪与排障。
    """

    def __init__(self, stale_after_hours: int) -> None:
        """
        初始化服务

        Args:
            stale_after_hours: 判定为陈旧 pending 的小时阈值
        """
        self.stale_after_hours = stale_after_hours

    async def cleanup_stale_pending_tasks(self) -> StalePendingTaskCleanupReport:
        """
        清理长时间未启动的 pending 创建任务

        Returns:
            清理结果报告
        """
        report = StalePendingTaskCleanupReport()
        logger.info(
            "stale_pending_task_cleanup_starting",
            stale_after_hours=self.stale_after_hours,
        )

        async with async_session_maker.begin() as session:
            task_crud = get_task_crud()
            stale_tasks = await task_crud.find_stale_pending_creation_tasks(
                session=session,
                stale_after_hours=self.stale_after_hours,
            )
            report.total_found = len(stale_tasks)
            report.task_ids = [task.task_id for task in stale_tasks]

            for task in stale_tasks:
                cleanup_message = (
                    "系统已自动清理长时间未启动的 pending 创建任务。"
                    f"该任务在创建后超过 {self.stale_after_hours} 小时仍停留在 init，"
                    "通常意味着后台分发失败或队列消息已丢失。"
                )
                try:
                    updated = await task_crud.update_task_status(
                        session=session,
                        task_id=task.task_id,
                        status="failed",
                        current_step="stale_pending_cleaned",
                        error_message=cleanup_message,
                    )
                    if updated:
                        report.cleaned += 1
                        logger.warning(
                            "stale_pending_task_cleaned",
                            task_id=task.task_id,
                            created_at=task.created_at.isoformat() if task.created_at else None,
                            celery_task_id=task.celery_task_id,
                        )
                    else:
                        report.failed += 1
                except Exception as exc:
                    report.failed += 1
                    logger.error(
                        "stale_pending_task_cleanup_failed",
                        task_id=task.task_id,
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )

        logger.info(
            "stale_pending_task_cleanup_completed",
            total_found=report.total_found,
            cleaned=report.cleaned,
            failed=report.failed,
        )
        return report


stale_pending_task_cleanup_service = StalePendingTaskCleanupService(
    stale_after_hours=settings.STALE_PENDING_TASK_CLEANUP_AFTER_HOURS,
)


async def cleanup_stale_pending_tasks_on_startup() -> StalePendingTaskCleanupReport:
    """
    启动时清理历史孤儿 pending 任务

    Returns:
        清理结果报告
    """
    if not settings.ENABLE_STALE_PENDING_TASK_CLEANUP:
        logger.info("stale_pending_task_cleanup_disabled_by_config")
        return StalePendingTaskCleanupReport()

    return await stale_pending_task_cleanup_service.cleanup_stale_pending_tasks()
