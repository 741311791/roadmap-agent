"""
Celery 任务队列监控 API 端点

重构说明（DB-first + runtime-enriched 混合模式）：
- 列表/总览的主数据源改为 roadmap_tasks（DB 持久化），不再只依赖瞬时 inspect
- Celery inspect / AsyncResult 作为补充信息层，一旦超时会设置 inspect_available=False
- 详情接口先查业务任务，再补充 execution_logs 摘要和 Celery result backend 信息
- workers 接口修正为基于 stats+active 并集，空闲 worker 不再消失
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from app.config.settings import settings
from app.core.celery_app import celery_app
from app.models.database import User
from app.core.auth.deps import current_superuser
from celery.result import AsyncResult
from app.schemas.monitoring import (
    CeleryTaskCleanupBatchResponse,
    CeleryTaskCleanupResponse,
    CeleryTaskInfo,
    CeleryOverview,
    CeleryTaskListResponse,
    CeleryWorkerInfo,
    CeleryWorkerListResponse,
)
from app.core.rate_limiter import get_rate_limiter
from app.db.session import async_session_maker
from app.crud.crud_task import get_task_crud
from app.models.database import RoadmapTask
from app.db.redis_client import redis_client
from app.core.orchestrator.state_manager import StateManager
from app.core.celery_worker_heartbeat import get_live_worker_heartbeats
from app.services.workflows.generation.stale_task_cleanup_service import (
    stale_task_cleanup_service,
)

router = APIRouter(prefix="/celery", tags=["monitoring", "celery"])
logger = structlog.get_logger()

# Celery Inspect 操作的超时时间（秒）
CELERY_INSPECT_TIMEOUT = 3.0

# 状态映射：业务状态 → 对外展示状态（汇总给前端）
WORKFLOW_STATUS_TO_DISPLAY: Dict[str, str] = {
    "pending": "PENDING",
    "processing": "STARTED",
    "running": "STARTED",
    "human_review_pending": "STARTED",
    "human_review_required": "STARTED",
    "approved": "SUCCESS",
    "completed": "SUCCESS",
    "partial_failure": "SUCCESS",
    "failed": "FAILURE",
    "rejected": "FAILURE",
    "cancelled": "REVOKED",
}

# 任务类型显示名称
TASK_TYPE_DISPLAY: Dict[str, str] = {
    "creation": "路线图生成",
    "retry_tutorial": "教程重试",
    "retry_resources": "资源重试",
    "retry_quiz": "测验重试",
    "retry_batch": "批量重试",
}

MONITOR_STATUS_GROUPS: Dict[str, List[str]] = {
    "active": ["pending", "processing", "running"],
    "pending": ["pending"],
    "processing": ["processing", "running"],
    "human_review_pending": ["human_review_pending", "human_review_required"],
    "completed": ["completed", "partial_failure", "approved"],
    "failed": ["failed", "rejected"],
}

state_manager = StateManager()


# ============================================================
# 工具函数
# ============================================================

async def run_celery_inspect_with_timeout(func, timeout: float = CELERY_INSPECT_TIMEOUT):
    """
    在线程池中运行 Celery Inspect 操作，并添加超时控制

    Celery Inspect 操作是同步阻塞的，将其放入线程池执行并设置超时。
    超时或失败时返回空字典，而不是抛出异常。

    Args:
        func: 要执行的 Celery Inspect 函数
        timeout: 超时时间（秒）

    Returns:
        Inspect 操作的结果，超时或失败时返回 None（调用方应判断 None 代表不可用）
    """
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(func),
            timeout=timeout
        )
        return result or {}
    except asyncio.TimeoutError:
        logger.warning(
            "celery_inspect_timeout",
            operation=getattr(func, '__name__', str(func)),
            timeout=timeout,
        )
        return None
    except Exception as e:
        logger.error(
            "celery_inspect_error",
            operation=getattr(func, '__name__', str(func)),
            error=str(e),
            error_type=type(e).__name__,
        )
        return None


def parse_task_timestamp(timestamp: Optional[float]) -> Optional[str]:
    """
    解析任务时间戳为 ISO 格式字符串

    Args:
        timestamp: Unix 时间戳

    Returns:
        ISO 格式时间字符串，如果时间戳为 None 则返回 None
    """
    if timestamp is None:
        return None
    try:
        return datetime.fromtimestamp(timestamp).isoformat()
    except Exception:
        return None


def roadmap_task_to_celery_info(task: RoadmapTask, live_step: Optional[str] = None) -> CeleryTaskInfo:
    """
    将 RoadmapTask 业务任务转换为 CeleryTaskInfo 展示对象

    转换规则：
    - status 字段映射为对外的 Celery 状态显示（PENDING/STARTED/SUCCESS/FAILURE 等）
    - workflow_status 保留原始业务状态
    - task_id 使用业务 task_id
    - celery_task_id 使用原 Celery 任务 ID（runtime 补充字段）

    Args:
        task: RoadmapTask 业务任务对象
        live_step: Redis 实时步骤（可选，来自 StateManager）

    Returns:
        CeleryTaskInfo 展示对象
    """
    display_status = WORKFLOW_STATUS_TO_DISPLAY.get(task.status, task.status.upper())
    task_name = TASK_TYPE_DISPLAY.get(task.task_type or "", task.task_type or "unknown")

    # 计算执行耗时
    duration = None
    if task.completed_at and task.created_at:
        duration = (task.completed_at - task.created_at).total_seconds()

    return CeleryTaskInfo(
        task_id=task.task_id,
        task_name=task_name,
        status=display_status,
        workflow_status=task.status,
        current_step=live_step or task.current_step,
        task_type=task.task_type,
        roadmap_id=task.roadmap_id,
        celery_task_id=task.celery_task_id,
        content_generation_status=task.content_generation_status,
        error_message=task.error_message,
        started_at=task.created_at.isoformat() if task.created_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        duration=duration,
        live_step=live_step,
        source="database",
    )


def extract_runtime_task(task_data: Dict[str, Any], worker_name: str, status: str) -> CeleryTaskInfo:
    """
    从 Celery inspect 原始数据中提取 runtime 任务信息（不在 DB 中的纯 Celery 任务）

    Args:
        task_data: inspect 返回的任务数据
        worker_name: Worker 名称
        status: 任务状态（STARTED/SCHEDULED/RESERVED）

    Returns:
        CeleryTaskInfo 展示对象
    """
    if status == "SCHEDULED":
        # scheduled 任务的数据结构嵌套在 request 字段里
        request = task_data.get("request", {})
        task_id = request.get("id", "")
        task_name = request.get("name", "unknown")
        delivery_info = request.get("delivery_info", {})
        eta = task_data.get("eta")
        started_at = parse_task_timestamp(eta) if eta else None
        args = request.get("args")
        kwargs = request.get("kwargs")
    else:
        task_id = task_data.get("id", "")
        task_name = task_data.get("name", "unknown")
        delivery_info = task_data.get("delivery_info", {})
        time_start = task_data.get("time_start")
        started_at = parse_task_timestamp(time_start)
        args = task_data.get("args")
        kwargs = task_data.get("kwargs")

    queue = delivery_info.get("routing_key", "default")

    duration = None
    if status == "STARTED":
        time_start = task_data.get("time_start")
        if time_start:
            duration = datetime.now().timestamp() - time_start

    return CeleryTaskInfo(
        task_id=task_id,
        task_name=task_name,
        queue=queue,
        status=status,
        worker=worker_name,
        started_at=started_at,
        args=args,
        kwargs=kwargs,
        duration=duration,
        source="runtime",
    )


def enrich_task_cleanup_metadata(
    task_info: CeleryTaskInfo,
    task: RoadmapTask,
    runtime_task_ids: Optional[set[str]] = None,
) -> CeleryTaskInfo:
    """
    为业务任务补充卡住清理相关元数据

    Args:
        task_info: 已构建的展示对象
        task: 原始业务任务
        runtime_task_ids: Celery runtime 中可见的任务 ID 集合

    Returns:
        补充字段后的展示对象
    """
    is_stale, stale_for_seconds = stale_task_cleanup_service.get_staleness_metadata(task)
    has_runtime_presence = None
    can_safe_cleanup = False
    can_force_cleanup = False

    if runtime_task_ids is not None:
        has_runtime_presence = stale_task_cleanup_service.has_runtime_presence(
            task,
            runtime_task_ids,
        )
        can_safe_cleanup = task.status == "processing" and is_stale and not has_runtime_presence

    can_force_cleanup = task.status == "processing" and is_stale

    task_info.updated_at = task.updated_at.isoformat() if task.updated_at else None
    task_info.is_stale = is_stale
    task_info.stale_for_seconds = stale_for_seconds
    task_info.has_runtime_presence = has_runtime_presence
    task_info.can_safe_cleanup = can_safe_cleanup
    task_info.can_force_cleanup = can_force_cleanup
    return task_info


def resolve_monitor_status_filters(status: Optional[str]) -> Optional[List[str]]:
    """
    将监控页状态筛选转换为数据库状态列表

    设计原因：
    - 总览卡片展示的是聚合状态，而数据库里保存的是原子状态；
    - human_review_pending 表示流程暂停等待用户操作，不应混入 processing；
    - 通过统一映射，确保总览数字、卡片点击筛选、下拉筛选三者口径一致。

    Args:
        status: 前端传入的筛选值

    Returns:
        对应的数据库状态列表；若为空则返回 None
    """
    if not status or status == "all":
        return None

    legacy_map = {
        "scheduled": "pending",
        "reserved": "pending",
    }
    normalized_status = legacy_map.get(status, status)
    return MONITOR_STATUS_GROUPS.get(normalized_status, [normalized_status])


# ============================================================
# API 端点
# ============================================================

@router.get("/overview", response_model=CeleryOverview)
async def get_celery_overview(
    current_user: User = Depends(current_superuser),
):
    """
    获取管理员监控总览

    返回 DB 业务任务统计（始终有值）和 Celery runtime 统计（inspect 可用时有值）。
    当 inspect 超时或无 Worker 时，inspect_available=False，runtime 统计为 0，
    但 DB 统计正常返回，不再伪装成"无任何任务"。

    只有超级管理员可以访问。
    """
    logger.info("celery_overview_requested", admin_id=current_user.id)

    # ── DB 统计（始终执行）────────────────────────────────────
    async with async_session_maker() as session:
        task_crud = get_task_crud()

        # 当前活跃任务数（不限时间范围）
        active_counts = await task_crud.get_active_status_counts(session)
        db_processing_count = sum(active_counts.get(s, 0) for s in ["processing", "running"])
        db_pending_count = active_counts.get("pending", 0)
        db_total_active = db_processing_count + db_pending_count

        # 过去 24 小时的完成/失败数
        counts_24h = await task_crud.get_admin_status_counts(session, days=1)
        completed_statuses = {"completed", "partial_failure", "approved"}
        failed_statuses = {"failed", "rejected"}
        db_completed_24h = sum(counts_24h.get(s, 0) for s in completed_statuses)
        db_failed_24h = sum(counts_24h.get(s, 0) for s in failed_statuses)

    stale_processing_count = 0
    cleanable_stale_processing_count = 0
    force_cleanable_stale_processing_count = 0
    try:
        stale_processing_count, cleanable_stale_processing_count, force_cleanable_stale_processing_count = (
            await stale_task_cleanup_service.get_stale_task_counts()
        )
    except Exception as e:
        logger.warning("stale_task_counts_fetch_failed", error=str(e))

    heartbeat_workers: list[dict[str, Any]] = []
    try:
        heartbeat_workers = await get_live_worker_heartbeats()
    except Exception as e:
        logger.warning("heartbeat_workers_fetch_failed", error=str(e))

    # ── Celery runtime 统计（带超时保护）─────────────────────
    inspect = celery_app.control.inspect()

    active_result, scheduled_result, reserved_result, stats_result = await asyncio.gather(
        run_celery_inspect_with_timeout(inspect.active),
        run_celery_inspect_with_timeout(inspect.scheduled),
        run_celery_inspect_with_timeout(inspect.reserved),
        run_celery_inspect_with_timeout(inspect.stats),
        return_exceptions=False,
    )

    # 任何一个返回 None 都说明 inspect 不可用
    inspect_available = all(r is not None for r in [active_result, scheduled_result, reserved_result])
    active_tasks = active_result or {}
    scheduled_tasks = scheduled_result or {}
    reserved_tasks = reserved_result or {}
    stats_data = stats_result or {}

    runtime_active_count = sum(len(tasks) for tasks in active_tasks.values())
    scheduled_count = sum(len(tasks) for tasks in scheduled_tasks.values())
    reserved_count = sum(len(tasks) for tasks in reserved_tasks.values())
    runtime_pending_count = scheduled_count + reserved_count

    # Worker 在线数：stats 和 active 的键并集
    workers_set = set(stats_data.keys()) | set(active_tasks.keys())
    workers_online = len(workers_set)

    # 各队列长度：从三类任务中聚合
    queue_lengths: Dict[str, int] = {}
    for worker_tasks in active_tasks.values():
        for task in worker_tasks:
            q = task.get("delivery_info", {}).get("routing_key", "default")
            queue_lengths[q] = queue_lengths.get(q, 0) + 1
    for worker_tasks in scheduled_tasks.values():
        for task in worker_tasks:
            q = task.get("request", {}).get("delivery_info", {}).get("routing_key", "default")
            queue_lengths[q] = queue_lengths.get(q, 0) + 1
    for worker_tasks in reserved_tasks.values():
        for task in worker_tasks:
            q = task.get("delivery_info", {}).get("routing_key", "default")
            queue_lengths[q] = queue_lengths.get(q, 0) + 1

    logger.info(
        "celery_overview_success",
        admin_id=current_user.id,
        inspect_available=inspect_available,
        runtime_active_count=runtime_active_count,
        db_total_active=db_total_active,
    )

    return CeleryOverview(
        inspect_available=inspect_available,
        runtime_active_count=runtime_active_count,
        runtime_pending_count=runtime_pending_count,
        scheduled_count=scheduled_count,
        reserved_count=reserved_count,
        workers_online=workers_online,
        queue_lengths=queue_lengths,
        workers=list(workers_set),
        heartbeat_available=len(heartbeat_workers) > 0,
        heartbeat_workers_online=len(heartbeat_workers),
        heartbeat_workers=[item.get("hostname", "unknown") for item in heartbeat_workers],
        db_processing_count=db_processing_count,
        db_pending_count=db_pending_count,
        db_completed_24h=db_completed_24h,
        db_failed_24h=db_failed_24h,
        db_total_active=db_total_active,
        stale_processing_count=stale_processing_count,
        cleanable_stale_processing_count=cleanable_stale_processing_count,
        force_cleanable_stale_processing_count=force_cleanable_stale_processing_count,
    )


@router.get("/tasks", response_model=CeleryTaskListResponse)
async def get_celery_tasks(
    current_user: User = Depends(current_superuser),
    status: Optional[str] = Query(
        None,
        description="筛选业务状态组：active/pending/processing/human_review_pending/completed/failed 等",
    ),
    queue: Optional[str] = Query(None, description="筛选队列名称（runtime 任务专用）"),
    task_type: Optional[str] = Query(None, description="筛选任务类型: creation/retry_tutorial 等"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移量"),
):
    """
    获取管理员任务列表（DB-first）

    默认只返回最近 1 天的业务任务历史（来自 roadmap_tasks），
    以降低监控页列表加载开销，并支持按业务状态、任务类型筛选。
    只有超级管理员可以访问。
    """
    logger.info(
        "celery_tasks_requested",
        admin_id=current_user.id,
        status=status,
        task_type=task_type,
        limit=limit,
        offset=offset,
    )

    try:
        async with async_session_maker() as session:
            task_crud = get_task_crud()
            db_statuses = resolve_monitor_status_filters(status)

            tasks = await task_crud.get_admin_tasks(
                session,
                statuses=db_statuses,
                task_type=task_type,
                days=1,
                skip=offset,
                limit=limit,
            )
            total = await task_crud.count_admin_tasks(
                session,
                statuses=db_statuses,
                task_type=task_type,
                days=1,
            )

        # 批量获取 live_step（避免 N+1）
        live_steps: Dict[str, Optional[str]] = {}
        try:
            live_steps = await state_manager.get_all_live_steps()
        except Exception as e:
            logger.warning("live_steps_fetch_failed", error=str(e))

        runtime_task_ids: Optional[set[str]] = None
        try:
            runtime_task_ids = await stale_task_cleanup_service.get_runtime_task_ids()
        except Exception as e:
            logger.warning("runtime_task_ids_fetch_failed", error=str(e))

        task_infos = []
        for task in tasks:
            task_info = roadmap_task_to_celery_info(task, live_steps.get(task.task_id))
            task_infos.append(
                enrich_task_cleanup_metadata(
                    task_info=task_info,
                    task=task,
                    runtime_task_ids=runtime_task_ids,
                )
            )

        logger.info(
            "celery_tasks_success",
            admin_id=current_user.id,
            total=total,
            returned=len(task_infos),
        )

        return CeleryTaskListResponse(tasks=task_infos, total=total)

    except Exception as e:
        logger.error(
            "celery_tasks_failed",
            admin_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail=f"Failed to get tasks: {str(e)}")


@router.get("/tasks/{task_id}", response_model=CeleryTaskInfo)
async def get_celery_task_detail(
    task_id: str,
    current_user: User = Depends(current_superuser),
):
    """
    获取任务详情（业务优先，Celery 补充）

    优先按业务 task_id 查询 roadmap_tasks，
    再拼接 live_step 和 Celery result backend 的结果/错误信息。
    若按业务 task_id 查不到，自动 fallback 到按 Celery 原生 task_id 查询 AsyncResult。

    只有超级管理员可以访问。
    """
    logger.info(
        "celery_task_detail_requested",
        admin_id=current_user.id,
        task_id=task_id,
    )

    try:
        async with async_session_maker() as session:
            task_crud = get_task_crud()

            # 第一步：按业务 task_id 查询
            task = await task_crud.get_by_task_id(session, task_id)

            # 第二步：如果未找到，尝试按 Celery task_id 反查
            if not task:
                task = await task_crud.get_by_celery_task_id(session, task_id)

        if task:
            # 获取 live_step
            live_step: Optional[str] = None
            try:
                live_step = await state_manager.get_live_step(task.task_id)
            except Exception:
                pass

            task_info = roadmap_task_to_celery_info(task, live_step)
            runtime_task_ids: Optional[set[str]] = None
            try:
                runtime_task_ids = await stale_task_cleanup_service.get_runtime_task_ids()
            except Exception as e:
                logger.warning("runtime_task_ids_fetch_failed_for_detail", error=str(e))

            task_info = enrich_task_cleanup_metadata(
                task_info=task_info,
                task=task,
                runtime_task_ids=runtime_task_ids,
            )
            task_info.source = "hybrid"

            # 用 Celery result backend 补充结果/错误
            celery_id = task.celery_task_id or task.content_generation_celery_id
            if celery_id:
                try:
                    async_result = AsyncResult(celery_id, app=celery_app)
                    if async_result.successful():
                        task_info.result = async_result.result
                    elif async_result.failed():
                        if not task_info.error_message:
                            task_info.error = str(async_result.info)
                except Exception as e:
                    logger.warning(
                        "celery_result_fetch_failed",
                        task_id=task_id,
                        celery_id=celery_id,
                        error=str(e),
                    )

        else:
            # Fallback：纯 Celery AsyncResult（task_id 本身就是 Celery ID）
            logger.info(
                "celery_task_detail_fallback_to_async_result",
                admin_id=current_user.id,
                task_id=task_id,
            )
            async_result = AsyncResult(task_id, app=celery_app)
            task_info = CeleryTaskInfo(
                task_id=task_id,
                task_name=async_result.name or "unknown",
                status=async_result.status,
                source="runtime",
            )
            if async_result.successful():
                try:
                    task_info.result = async_result.result
                except Exception:
                    pass
            elif async_result.failed():
                try:
                    task_info.error = str(async_result.info)
                except Exception:
                    pass
            try:
                info = async_result.info
                if isinstance(info, dict):
                    task_info.started_at = info.get("started_at")
                    task_info.completed_at = info.get("completed_at")
            except Exception:
                pass

        logger.info(
            "celery_task_detail_success",
            admin_id=current_user.id,
            task_id=task_id,
            source=task_info.source,
            status=task_info.status,
        )
        return task_info

    except Exception as e:
        logger.error(
            "celery_task_detail_failed",
            admin_id=current_user.id,
            task_id=task_id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to get task detail: {str(e)}")


@router.post("/tasks/{task_id}/cleanup-stale", response_model=CeleryTaskCleanupResponse)
async def cleanup_stale_task(
    task_id: str,
    current_user: User = Depends(current_superuser),
):
    """
    管理员手动清理单个卡住任务

    仅允许清理：
    - 业务状态为 processing
    - 已超过卡住阈值
    - Celery runtime 中已不可见
    """
    logger.warning(
        "admin_cleanup_stale_task_requested",
        admin_id=current_user.id,
        task_id=task_id,
    )

    try:
        return await stale_task_cleanup_service.cleanup_task_by_id(
            task_id=task_id,
            trigger="admin_button",
            actor_id=current_user.id,
            force=False,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except RuntimeError as e:
        error_message = str(e)
        status_code = (
            status.HTTP_503_SERVICE_UNAVAILABLE
            if "inspect" in error_message
            else status.HTTP_409_CONFLICT
        )
        raise HTTPException(status_code=status_code, detail=error_message) from e
    except Exception as e:
        logger.error(
            "admin_cleanup_stale_task_failed",
            admin_id=current_user.id,
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup stale task: {str(e)}",
        ) from e


@router.post("/tasks/stale/cleanup", response_model=CeleryTaskCleanupBatchResponse)
async def cleanup_stale_tasks(
    current_user: User = Depends(current_superuser),
):
    """
    管理员批量清理卡住任务

    按配置的卡住阈值扫描 processing 任务，并只清理
    Celery runtime 中已不可见的脏任务。
    """
    logger.warning(
        "admin_cleanup_stale_tasks_requested",
        admin_id=current_user.id,
        stale_after_minutes=settings.STALE_TASK_CLEANUP_AFTER_MINUTES,
    )

    try:
        return await stale_task_cleanup_service.sweep_stale_tasks(
            trigger="admin_bulk",
            actor_id=current_user.id,
            force=False,
        )
    except Exception as e:
        logger.error(
            "admin_cleanup_stale_tasks_failed",
            admin_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup stale tasks: {str(e)}",
        ) from e


@router.post("/tasks/{task_id}/force-cleanup-stale", response_model=CeleryTaskCleanupResponse)
async def force_cleanup_stale_task(
    task_id: str,
    current_user: User = Depends(current_superuser),
):
    """
    管理员强制清理单个卡住任务

    当 inspect 不可用时，允许管理员绕过 runtime 可见性校验，
    直接将 stale processing 任务标记为失败。
    """
    logger.warning(
        "admin_force_cleanup_stale_task_requested",
        admin_id=current_user.id,
        task_id=task_id,
    )

    try:
        return await stale_task_cleanup_service.cleanup_task_by_id(
            task_id=task_id,
            trigger="admin_force_button",
            actor_id=current_user.id,
            force=True,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(
            "admin_force_cleanup_stale_task_failed",
            admin_id=current_user.id,
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to force cleanup stale task: {str(e)}",
        ) from e


@router.post("/tasks/stale/force-cleanup", response_model=CeleryTaskCleanupBatchResponse)
async def force_cleanup_stale_tasks(
    current_user: User = Depends(current_superuser),
):
    """
    管理员批量强制清理卡住任务
    """
    logger.warning(
        "admin_force_cleanup_stale_tasks_requested",
        admin_id=current_user.id,
        stale_after_minutes=settings.STALE_TASK_CLEANUP_AFTER_MINUTES,
    )

    try:
        return await stale_task_cleanup_service.sweep_stale_tasks(
            trigger="admin_force_bulk",
            actor_id=current_user.id,
            force=True,
        )
    except Exception as e:
        logger.error(
            "admin_force_cleanup_stale_tasks_failed",
            admin_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to force cleanup stale tasks: {str(e)}",
        ) from e


@router.get("/workers", response_model=CeleryWorkerListResponse)
async def get_celery_workers(
    current_user: User = Depends(current_superuser),
):
    """
    获取 Celery Worker 列表

    以 inspect.stats() 键为主，联合 inspect.active() 补活动任务数，
    空闲 Worker 不再因为没有活跃任务而从列表消失。
    只有超级管理员可以访问。
    """
    logger.info("celery_workers_requested", admin_id=current_user.id)

    try:
        inspect = celery_app.control.inspect()

        active_result, stats_result = await asyncio.gather(
            run_celery_inspect_with_timeout(inspect.active),
            run_celery_inspect_with_timeout(inspect.stats),
        )

        active_tasks = active_result or {}
        stats_data = stats_result or {}

        workers: List[CeleryWorkerInfo] = []

        # inspect 可用时，优先展示 runtime 结果
        if active_result is not None or stats_result is not None:
            all_workers = set(stats_data.keys()) | set(active_tasks.keys())
            for worker_name in all_workers:
                worker_stats = stats_data.get(worker_name, {})
                total_dict = worker_stats.get("total", {}) if worker_stats else {}
                processed = sum(total_dict.values()) if isinstance(total_dict, dict) else 0

                workers.append(CeleryWorkerInfo(
                    hostname=worker_name,
                    status="online",
                    active_tasks=len(active_tasks.get(worker_name, [])),
                    processed_tasks=processed if processed > 0 else None,
                    source="inspect",
                ))
        else:
            heartbeat_workers = await get_live_worker_heartbeats()
            workers = [
                CeleryWorkerInfo(
                    hostname=item.get("hostname", "unknown"),
                    status="online",
                    active_tasks=0,
                    processed_tasks=None,
                    last_seen_at=item.get("updated_at"),
                    source="heartbeat",
                )
                for item in heartbeat_workers
            ]

        logger.info(
            "celery_workers_success",
            admin_id=current_user.id,
            total=len(workers),
        )

        return CeleryWorkerListResponse(workers=workers, total=len(workers))

    except Exception as e:
        logger.error(
            "celery_workers_failed",
            admin_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to get workers: {str(e)}")


# ============================================================
# API 速率限制监控端点
# ============================================================

@router.get("/api-rate-limits", response_model=Dict[str, Any])
async def get_api_rate_limits(
    current_user: User = Depends(current_superuser),
):
    """
    获取所有 API 的速率限制使用情况

    返回各 API Provider 的当前速率使用情况，包括：
    - current_count: 当前 1 分钟窗口内的请求数
    - limit: 配置的速率限制（RPM）
    - usage_percent: 使用率百分比
    - available: 剩余可用次数

    只有超级管理员可以访问。
    """
    logger.info("api_rate_limits_requested", admin_id=current_user.id)

    try:
        rate_limiter = get_rate_limiter()
        usage_data = await rate_limiter.get_all_usage()
        stats_data = rate_limiter.get_stats()

        logger.info("api_rate_limits_success", admin_id=current_user.id)

        return {
            "usage": usage_data,
            "statistics": stats_data,
        }

    except Exception as e:
        logger.error(
            "api_rate_limits_failed",
            admin_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to get API rate limits: {str(e)}")


@router.get("/api-rate-limits/{provider}", response_model=Dict[str, Any])
async def get_api_rate_limit_by_provider(
    provider: str,
    current_user: User = Depends(current_superuser),
):
    """
    获取指定 API Provider 的速率限制使用情况

    Args:
        provider: API Provider 名称（如 openai, anthropic, deepseek, tavily）
    """
    logger.info(
        "api_rate_limit_by_provider_requested",
        admin_id=current_user.id,
        provider=provider,
    )

    try:
        rate_limiter = get_rate_limiter()
        usage_data = await rate_limiter.get_current_usage(provider)
        logger.info("api_rate_limit_by_provider_success", admin_id=current_user.id, provider=provider)
        return usage_data

    except Exception as e:
        logger.error(
            "api_rate_limit_by_provider_failed",
            admin_id=current_user.id,
            provider=provider,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to get API rate limit for {provider}: {str(e)}")


@router.post("/api-rate-limits/{provider}/reset", response_model=Dict[str, Any])
async def reset_api_rate_limit(
    provider: str,
    current_user: User = Depends(current_superuser),
):
    """
    重置指定 API Provider 的速率限制（清空窗口记录）

    用于紧急情况下清空某个 Provider 的请求记录，重置速率限制。

    Args:
        provider: API Provider 名称（如 openai, anthropic, deepseek, tavily）
    """
    logger.info(
        "api_rate_limit_reset_requested",
        admin_id=current_user.id,
        provider=provider,
    )

    try:
        rate_limiter = get_rate_limiter()
        success = await rate_limiter.reset_provider(provider)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Provider '{provider}' not found or not supported"
            )

        logger.info("api_rate_limit_reset_success", admin_id=current_user.id, provider=provider)

        return {
            "success": True,
            "message": f"Rate limit for {provider} has been reset",
            "provider": provider,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "api_rate_limit_reset_failed",
            admin_id=current_user.id,
            provider=provider,
            error=str(e),
        )
        raise HTTPException(status_code=500, detail=f"Failed to reset API rate limit for {provider}: {str(e)}")
