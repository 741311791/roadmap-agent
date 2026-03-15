"""
卡住任务清理服务

负责两类场景：
1. 管理员在监控页手动清理长期卡在 processing 的任务。
2. 后台 watchdog 周期性扫描并自动回收长期未更新的脏任务。
"""

import asyncio
from typing import Optional

import structlog
from celery.result import AsyncResult

from app.config.settings import settings
from app.core.celery_app import celery_app
from app.core.orchestrator.state_manager import StateManager
from app.crud.crud_task import get_task_crud
from app.db.session import async_session_maker
from app.models.database import RoadmapTask, beijing_now
from app.schemas.monitoring import (
    CeleryTaskCleanupBatchResponse,
    CeleryTaskCleanupResponse,
)

logger = structlog.get_logger()

# 复用监控接口的超时策略，避免 inspect 阻塞请求与后台循环。
CELERY_INSPECT_TIMEOUT_SECONDS = 3.0
CELERY_REVOKE_TIMEOUT_SECONDS = 3.0


class StaleTaskCleanupService:
    """
    卡住任务清理服务

    设计原则：
    - 只处理 status=processing 且长时间未更新的任务。
    - 清理前必须确认 Celery runtime 中已不可见，避免误杀真实仍在运行的任务。
    - 手动清理与后台 watchdog 复用同一套逻辑。
    """

    def __init__(
        self,
        stale_after_minutes: int,
        interval_seconds: int,
        batch_size: int,
    ) -> None:
        """
        初始化卡住任务清理服务

        Args:
            stale_after_minutes: 任务判定为卡住的分钟阈值
            interval_seconds: watchdog 扫描间隔（秒）
            batch_size: 单次扫描最多处理的任务数量
        """
        self.stale_after_minutes = stale_after_minutes
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size
        self.state_manager = StateManager()
        self._watchdog_task: Optional[asyncio.Task] = None

    def get_staleness_metadata(self, task: RoadmapTask) -> tuple[bool, Optional[float]]:
        """
        计算任务是否已达到“卡住”阈值

        Args:
            task: 业务任务

        Returns:
            tuple[bool, Optional[float]]:
                - 是否卡住
                - 距离最近更新时间已经过去的秒数
        """
        if task.status != "processing" or not task.updated_at:
            return False, None

        stale_for_seconds = (beijing_now() - task.updated_at).total_seconds()
        is_stale = stale_for_seconds >= self.stale_after_minutes * 60
        return is_stale, max(stale_for_seconds, 0.0)

    async def cleanup_task_by_id(
        self,
        task_id: str,
        *,
        trigger: str,
        actor_id: Optional[str] = None,
        allow_non_stale: bool = False,
        force: bool = False,
    ) -> CeleryTaskCleanupResponse:
        """
        按 task_id 清理单个卡住任务

        Args:
            task_id: 业务任务 ID
            trigger: 触发来源（如 admin_button、watchdog）
            actor_id: 操作者 ID（管理员触发时记录）
            allow_non_stale: 是否允许绕过卡住阈值校验
            force: 是否强制清理（绕过 runtime 可见性校验）

        Returns:
            单个任务清理结果

        Raises:
            ValueError: 任务不存在、状态不匹配或未达到卡住阈值
            RuntimeError: Celery inspect 不可用或任务仍在 runtime 中可见
        """
        runtime_task_ids = await self.get_runtime_task_ids()
        if runtime_task_ids is None and not force:
            raise RuntimeError("Celery inspect 当前不可用，无法安全清理任务")

        async with async_session_maker() as session:
            task_crud = get_task_crud()
            task = await task_crud.get_by_task_id(session, task_id)

        if not task:
            raise ValueError(f"任务不存在：{task_id}")

        return await self._cleanup_task_record(
            task=task,
            runtime_task_ids=runtime_task_ids or set(),
            trigger=trigger,
            actor_id=actor_id,
            allow_non_stale=allow_non_stale,
            force=force,
        )

    async def get_stale_task_counts(self) -> tuple[int, int, int]:
        """
        获取当前卡住任务统计

        Returns:
            tuple[int, int, int]:
                - stale_count: 已达到卡住阈值的 processing 任务数
                - cleanable_count: 其中当前可安全清理的任务数
                - force_cleanable_count: 当前可强制清理的任务数
        """
        async with async_session_maker() as session:
            task_crud = get_task_crud()
            stale_count = await task_crud.count_stale_processing_tasks(
                session=session,
                stale_after_minutes=self.stale_after_minutes,
            )
            if stale_count == 0:
                return 0, 0, 0

            stale_tasks = await task_crud.find_stale_processing_tasks(
                session=session,
                stale_after_minutes=self.stale_after_minutes,
                limit=None,
            )

        runtime_task_ids = await self.get_runtime_task_ids()
        if runtime_task_ids is None:
            return stale_count, 0, stale_count

        cleanable_count = sum(
            1 for task in stale_tasks
            if not self.has_runtime_presence(task, runtime_task_ids)
        )
        return stale_count, cleanable_count, stale_count

    async def sweep_stale_tasks(
        self,
        *,
        trigger: str,
        actor_id: Optional[str] = None,
        force: bool = False,
    ) -> CeleryTaskCleanupBatchResponse:
        """
        批量扫描并清理卡住任务

        Args:
            trigger: 触发来源（如 admin_bulk、watchdog）
            actor_id: 操作者 ID（管理员批量清理时记录）
            force: 是否强制清理（绕过 runtime 可见性校验）

        Returns:
            批量清理结果
        """
        async with async_session_maker() as session:
            task_crud = get_task_crud()
            stale_tasks = await task_crud.find_stale_processing_tasks(
                session=session,
                stale_after_minutes=self.stale_after_minutes,
                limit=self.batch_size,
            )

        task_ids = [task.task_id for task in stale_tasks]
        if not stale_tasks:
            return CeleryTaskCleanupBatchResponse(
                scanned=0,
                cleaned=0,
                skipped=0,
                failed=0,
                task_ids=[],
                cleanup_mode="force" if force else "safe",
                message="未发现需要清理的卡住任务",
            )

        runtime_task_ids = await self.get_runtime_task_ids()
        if runtime_task_ids is None and not force:
            return CeleryTaskCleanupBatchResponse(
                scanned=len(stale_tasks),
                cleaned=0,
                skipped=len(stale_tasks),
                failed=0,
                task_ids=task_ids,
                cleanup_mode="safe",
                message="Celery inspect 当前不可用，已跳过本轮自动清理",
            )

        cleaned = 0
        skipped = 0
        failed = 0

        for task in stale_tasks:
            try:
                await self._cleanup_task_record(
                    task=task,
                    runtime_task_ids=runtime_task_ids or set(),
                    force=force,
                    trigger=trigger,
                    actor_id=actor_id,
                    allow_non_stale=True,
                )
                cleaned += 1
            except ValueError:
                skipped += 1
            except RuntimeError:
                skipped += 1
            except Exception as exc:
                failed += 1
                logger.error(
                    "stale_task_cleanup_batch_item_failed",
                    task_id=task.task_id,
                    trigger=trigger,
                    actor_id=actor_id,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )

        return CeleryTaskCleanupBatchResponse(
            scanned=len(stale_tasks),
            cleaned=cleaned,
            skipped=skipped,
            failed=failed,
            task_ids=task_ids,
            cleanup_mode="force" if force else "safe",
            message=(
                f"本轮扫描 {len(stale_tasks)} 个候选任务，"
                f"成功清理 {cleaned} 个，跳过 {skipped} 个，失败 {failed} 个"
            ),
        )

    async def start_watchdog(self) -> None:
        """
        启动后台 watchdog 循环
        """
        if not settings.ENABLE_STALE_TASK_WATCHDOG:
            logger.info("stale_task_watchdog_disabled_by_config")
            return

        if self._watchdog_task and not self._watchdog_task.done():
            logger.info("stale_task_watchdog_already_running")
            return

        self._watchdog_task = asyncio.create_task(
            self._watchdog_loop(),
            name="stale_task_watchdog_loop",
        )
        logger.info(
            "stale_task_watchdog_started",
            interval_seconds=self.interval_seconds,
            stale_after_minutes=self.stale_after_minutes,
            batch_size=self.batch_size,
        )

    async def stop_watchdog(self) -> None:
        """
        停止后台 watchdog 循环
        """
        if not self._watchdog_task:
            return

        self._watchdog_task.cancel()
        try:
            await self._watchdog_task
        except asyncio.CancelledError:
            logger.info("stale_task_watchdog_cancelled")
        finally:
            self._watchdog_task = None

    async def get_runtime_task_ids(self) -> Optional[set[str]]:
        """
        获取当前 Celery runtime 中可见的任务 ID 集合

        Returns:
            任务 ID 集合；当 inspect 不可用时返回 None
        """
        inspect = celery_app.control.inspect()

        active_result, scheduled_result, reserved_result = await asyncio.gather(
            self._run_inspect_call(inspect.active),
            self._run_inspect_call(inspect.scheduled),
            self._run_inspect_call(inspect.reserved),
        )

        if any(result is None for result in [active_result, scheduled_result, reserved_result]):
            return None

        runtime_task_ids: set[str] = set()

        for worker_tasks in (active_result or {}).values():
            for task in worker_tasks:
                task_id = task.get("id")
                if task_id:
                    runtime_task_ids.add(task_id)

        for worker_tasks in (reserved_result or {}).values():
            for task in worker_tasks:
                task_id = task.get("id")
                if task_id:
                    runtime_task_ids.add(task_id)

        for worker_tasks in (scheduled_result or {}).values():
            for task in worker_tasks:
                request = task.get("request", {})
                task_id = request.get("id")
                if task_id:
                    runtime_task_ids.add(task_id)

        return runtime_task_ids

    async def _watchdog_loop(self) -> None:
        """
        后台 watchdog 循环
        """
        try:
            while True:
                try:
                    result = await self.sweep_stale_tasks(trigger="watchdog")
                    if result.scanned > 0:
                        logger.info(
                            "stale_task_watchdog_cycle_completed",
                            scanned=result.scanned,
                            cleaned=result.cleaned,
                            skipped=result.skipped,
                            failed=result.failed,
                        )
                except Exception as exc:
                    logger.error(
                        "stale_task_watchdog_cycle_failed",
                        error=str(exc),
                        error_type=type(exc).__name__,
                    )

                await asyncio.sleep(self.interval_seconds)
        except asyncio.CancelledError:
            logger.info("stale_task_watchdog_loop_stopped")
            raise

    async def _cleanup_task_record(
        self,
        *,
        task: RoadmapTask,
        runtime_task_ids: set[str],
        trigger: str,
        actor_id: Optional[str],
        allow_non_stale: bool,
        force: bool,
    ) -> CeleryTaskCleanupResponse:
        """
        清理单个任务记录

        Args:
            task: 待清理的业务任务
            runtime_task_ids: 本轮获取的 runtime 任务 ID 集合
            trigger: 触发来源
            actor_id: 操作者 ID
            allow_non_stale: 是否跳过卡住阈值判断

        Returns:
            单个任务清理结果
        """
        if task.status != "processing":
            raise ValueError(f"任务状态不是 processing：{task.task_id}")

        is_stale, stale_for_seconds = self.get_staleness_metadata(task)
        if not allow_non_stale and not is_stale:
            raise ValueError(
                f"任务尚未达到卡住阈值（阈值 {self.stale_after_minutes} 分钟）：{task.task_id}"
            )

        runtime_visible = self.has_runtime_presence(task, runtime_task_ids)
        if runtime_visible and not force:
            raise RuntimeError(f"任务仍在 Celery runtime 中可见，跳过清理：{task.task_id}")

        await self._revoke_known_celery_tasks(task)
        await self.state_manager.clear_live_step(task.task_id)

        cleanup_message = (
            f"系统已将长期未更新的 processing 任务标记为失败。"
            f"触发来源：{trigger}。"
            f"清理模式：{'force' if force else 'safe'}。"
            f"最近更新时间距今约 {int(stale_for_seconds or 0)} 秒。"
        )

        async with async_session_maker.begin() as session:
            task_crud = get_task_crud()
            updated = await task_crud.update_task_status(
                session=session,
                task_id=task.task_id,
                status="failed",
                current_step="stale_processing_cleaned",
                error_message=cleanup_message,
            )
            if not updated:
                raise ValueError(f"任务不存在或更新失败：{task.task_id}")

        logger.warning(
            "stale_task_cleaned",
            task_id=task.task_id,
            trigger=trigger,
            actor_id=actor_id,
            stale_for_seconds=stale_for_seconds,
            celery_task_id=task.celery_task_id,
            content_generation_celery_id=task.content_generation_celery_id,
        )

        return CeleryTaskCleanupResponse(
            success=True,
            task_id=task.task_id,
            previous_status="processing",
            cleanup_status="failed",
            stale_for_seconds=stale_for_seconds,
            runtime_visible=runtime_visible,
            cleanup_mode="force" if force else "safe",
            message=cleanup_message,
        )

    async def _run_inspect_call(self, func) -> Optional[dict]:
        """
        执行 Celery inspect 调用并附带超时保护

        Args:
            func: inspect 调用函数

        Returns:
            inspect 结果；超时或异常时返回 None
        """
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(func),
                timeout=CELERY_INSPECT_TIMEOUT_SECONDS,
            )
            return result or {}
        except asyncio.TimeoutError:
            logger.warning(
                "stale_task_cleanup_inspect_timeout",
                operation=getattr(func, "__name__", str(func)),
                timeout=CELERY_INSPECT_TIMEOUT_SECONDS,
            )
            return None
        except Exception as exc:
            logger.error(
                "stale_task_cleanup_inspect_failed",
                operation=getattr(func, "__name__", str(func)),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return None

    def has_runtime_presence(self, task: RoadmapTask, runtime_task_ids: set[str]) -> bool:
        """
        判断业务任务是否仍在 Celery runtime 中可见

        Args:
            task: 业务任务
            runtime_task_ids: 当前 runtime 任务 ID 集合

        Returns:
            是否仍在 runtime 中可见
        """
        candidate_ids = {
            task.celery_task_id,
            task.content_generation_celery_id,
        }
        return any(candidate_id in runtime_task_ids for candidate_id in candidate_ids if candidate_id)

    async def _revoke_known_celery_tasks(self, task: RoadmapTask) -> None:
        """
        尝试撤销与业务任务关联的 Celery 任务 ID

        这里不使用 terminate，避免误伤 Worker 进程。

        Args:
            task: 业务任务
        """
        for celery_task_id in [task.celery_task_id, task.content_generation_celery_id]:
            if not celery_task_id:
                continue

            celery_result = AsyncResult(celery_task_id, app=celery_app)
            loop = asyncio.get_running_loop()

            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, celery_result.revoke),
                    timeout=CELERY_REVOKE_TIMEOUT_SECONDS,
                )
                logger.info(
                    "stale_task_cleanup_revoke_sent",
                    task_id=task.task_id,
                    celery_task_id=celery_task_id,
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "stale_task_cleanup_revoke_timeout",
                    task_id=task.task_id,
                    celery_task_id=celery_task_id,
                    timeout=CELERY_REVOKE_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                logger.warning(
                    "stale_task_cleanup_revoke_failed",
                    task_id=task.task_id,
                    celery_task_id=celery_task_id,
                    error=str(exc),
                    error_type=type(exc).__name__,
                )


stale_task_cleanup_service = StaleTaskCleanupService(
    stale_after_minutes=settings.STALE_TASK_CLEANUP_AFTER_MINUTES,
    interval_seconds=settings.STALE_TASK_WATCHDOG_INTERVAL_SECONDS,
    batch_size=settings.STALE_TASK_WATCHDOG_BATCH_SIZE,
)
