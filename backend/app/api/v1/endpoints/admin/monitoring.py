"""
Celery 任务队列监控 API 端点

提供实时的 Celery 任务状态查询功能，用于管理员监控任务队列。
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Query
import structlog

from app.core.celery_app import celery_app
from app.models.database import User
from app.core.auth.deps import current_superuser
from celery.result import AsyncResult
from app.schemas.monitoring import (
    CeleryTaskInfo,
    CeleryOverview,
    CeleryTaskListResponse,
    CeleryWorkerInfo,
    CeleryWorkerListResponse,
)
from app.core.rate_limiter import get_rate_limiter

router = APIRouter(prefix="/celery", tags=["monitoring", "celery"])
logger = structlog.get_logger()

# Celery Inspect 操作的超时时间（秒）
CELERY_INSPECT_TIMEOUT = 3.0


# ============================================================
# 工具函数
# ============================================================

async def run_celery_inspect_with_timeout(func, timeout: float = CELERY_INSPECT_TIMEOUT):
    """
    在线程池中运行 Celery Inspect 操作，并添加超时控制
    
    Celery Inspect 操作是同步阻塞的，可能会导致长时间等待。
    将其放入线程池执行，并设置超时时间。
    
    Args:
        func: 要执行的 Celery Inspect 函数
        timeout: 超时时间（秒）
        
    Returns:
        Inspect 操作的结果，超时或失败时返回空字典
    """
    try:
        # 在线程池中执行同步的 Celery Inspect 操作
        result = await asyncio.wait_for(
            asyncio.to_thread(func),
            timeout=timeout
        )
        return result or {}
    except asyncio.TimeoutError:
        logger.warning(
            "celery_inspect_timeout",
            operation=func.__name__ if hasattr(func, '__name__') else str(func),
            timeout=timeout,
        )
        return {}
    except Exception as e:
        logger.error(
            "celery_inspect_error",
            operation=func.__name__ if hasattr(func, '__name__') else str(func),
            error=str(e),
            error_type=type(e).__name__,
        )
        return {}


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


def extract_task_info_from_active(task_data: Dict[str, Any], worker_name: str) -> CeleryTaskInfo:
    """
    从活跃任务数据中提取任务信息
    
    Args:
        task_data: Celery inspect.active() 返回的任务数据
        worker_name: Worker 名称
        
    Returns:
        CeleryTaskInfo 对象
    """
    task_id = task_data.get("id", "")
    task_name = task_data.get("name", "unknown")
    
    # 从 delivery_info 中提取队列名称
    delivery_info = task_data.get("delivery_info", {})
    queue = delivery_info.get("routing_key", "default")
    
    # 解析时间戳
    time_start = task_data.get("time_start")
    started_at = parse_task_timestamp(time_start)
    
    # 计算执行耗时
    duration = None
    if time_start:
        duration = datetime.now().timestamp() - time_start
    
    return CeleryTaskInfo(
        task_id=task_id,
        task_name=task_name,
        queue=queue,
        status="STARTED",
        worker=worker_name,
        started_at=started_at,
        args=task_data.get("args"),
        kwargs=task_data.get("kwargs"),
        duration=duration,
    )


def extract_task_info_from_scheduled(task_data: Dict[str, Any], worker_name: str) -> CeleryTaskInfo:
    """
    从预约任务数据中提取任务信息
    
    Args:
        task_data: Celery inspect.scheduled() 返回的任务数据
        worker_name: Worker 名称
        
    Returns:
        CeleryTaskInfo 对象
    """
    request = task_data.get("request", {})
    task_id = request.get("id", "")
    task_name = request.get("name", "unknown")
    
    # 从 delivery_info 中提取队列名称
    delivery_info = request.get("delivery_info", {})
    queue = delivery_info.get("routing_key", "default")
    
    # ETA 时间
    eta = task_data.get("eta")
    scheduled_at = parse_task_timestamp(eta) if eta else None
    
    return CeleryTaskInfo(
        task_id=task_id,
        task_name=task_name,
        queue=queue,
        status="SCHEDULED",
        worker=worker_name,
        started_at=scheduled_at,
        args=request.get("args"),
        kwargs=request.get("kwargs"),
    )


def extract_task_info_from_reserved(task_data: Dict[str, Any], worker_name: str) -> CeleryTaskInfo:
    """
    从保留任务数据中提取任务信息
    
    Args:
        task_data: Celery inspect.reserved() 返回的任务数据
        worker_name: Worker 名称
        
    Returns:
        CeleryTaskInfo 对象
    """
    task_id = task_data.get("id", "")
    task_name = task_data.get("name", "unknown")
    
    # 从 delivery_info 中提取队列名称
    delivery_info = task_data.get("delivery_info", {})
    queue = delivery_info.get("routing_key", "default")
    
    return CeleryTaskInfo(
        task_id=task_id,
        task_name=task_name,
        queue=queue,
        status="RESERVED",
        worker=worker_name,
        args=task_data.get("args"),
        kwargs=task_data.get("kwargs"),
    )


def get_task_result_info(task_id: str) -> CeleryTaskInfo:
    """
    通过 AsyncResult 获取任务详细信息
    
    Args:
        task_id: 任务 ID
        
    Returns:
        CeleryTaskInfo 对象
    """
    result = AsyncResult(task_id, app=celery_app)
    
    task_info = CeleryTaskInfo(
        task_id=task_id,
        task_name=result.name or "unknown",
        status=result.status,
    )
    
    # 如果任务成功，获取结果
    if result.successful():
        try:
            task_info.result = result.result
        except Exception as e:
            logger.warning("failed_to_get_task_result", task_id=task_id, error=str(e))
    
    # 如果任务失败，获取错误信息
    if result.failed():
        try:
            task_info.error = str(result.info)
        except Exception as e:
            logger.warning("failed_to_get_task_error", task_id=task_id, error=str(e))
    
    # 获取任务元数据（如果可用）
    try:
        info = result.info
        if isinstance(info, dict):
            task_info.started_at = info.get("started_at")
            task_info.completed_at = info.get("completed_at")
    except Exception:
        pass
    
    return task_info


# ============================================================
# API 端点
# ============================================================

@router.get("/overview", response_model=CeleryOverview)
async def get_celery_overview(
    current_user: User = Depends(current_superuser),
):
    """
    获取 Celery 任务队列总览
    
    返回当前队列中的任务统计信息，包括活跃、待处理任务数和队列长度。
    只有超级管理员可以访问。
    
    Returns:
        Celery 任务队列总览数据
    """
    logger.info(
        "celery_overview_requested",
        admin_id=current_user.id,
    )
    
    try:
        # 获取 Inspector 实例
        inspect = celery_app.control.inspect()
        
        # 并发查询各类任务（带超时控制）
        active_tasks, scheduled_tasks, reserved_tasks = await asyncio.gather(
            run_celery_inspect_with_timeout(inspect.active),
            run_celery_inspect_with_timeout(inspect.scheduled),
            run_celery_inspect_with_timeout(inspect.reserved),
            return_exceptions=True,
        )
        
        # 处理异常结果
        if isinstance(active_tasks, Exception):
            logger.error("active_tasks_query_failed", error=str(active_tasks))
            active_tasks = {}
        if isinstance(scheduled_tasks, Exception):
            logger.error("scheduled_tasks_query_failed", error=str(scheduled_tasks))
            scheduled_tasks = {}
        if isinstance(reserved_tasks, Exception):
            logger.error("reserved_tasks_query_failed", error=str(reserved_tasks))
            reserved_tasks = {}
        
        # 统计任务数量
        active_count = sum(len(tasks) for tasks in active_tasks.values())
        scheduled_count = sum(len(tasks) for tasks in scheduled_tasks.values())
        reserved_count = sum(len(tasks) for tasks in reserved_tasks.values())
        pending_count = scheduled_count + reserved_count
        
        # 统计各队列长度
        queue_lengths: Dict[str, int] = {}
        
        # 从活跃任务中统计
        for worker_tasks in active_tasks.values():
            for task in worker_tasks:
                delivery_info = task.get("delivery_info", {})
                queue = delivery_info.get("routing_key", "default")
                queue_lengths[queue] = queue_lengths.get(queue, 0) + 1
        
        # 从预约任务中统计
        for worker_tasks in scheduled_tasks.values():
            for task in worker_tasks:
                request = task.get("request", {})
                delivery_info = request.get("delivery_info", {})
                queue = delivery_info.get("routing_key", "default")
                queue_lengths[queue] = queue_lengths.get(queue, 0) + 1
        
        # 从保留任务中统计
        for worker_tasks in reserved_tasks.values():
            for task in worker_tasks:
                delivery_info = task.get("delivery_info", {})
                queue = delivery_info.get("routing_key", "default")
                queue_lengths[queue] = queue_lengths.get(queue, 0) + 1
        
        # 获取 Worker 列表
        workers = list(active_tasks.keys())
        
        logger.info(
            "celery_overview_success",
            admin_id=current_user.id,
            active_count=active_count,
            pending_count=pending_count,
        )
        
        return CeleryOverview(
            active_count=active_count,
            pending_count=pending_count,
            scheduled_count=scheduled_count,
            reserved_count=reserved_count,
            queue_lengths=queue_lengths,
            workers=workers,
        )
        
    except Exception as e:
        logger.error(
            "celery_overview_failed",
            admin_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Celery overview: {str(e)}"
        )


@router.get("/tasks", response_model=CeleryTaskListResponse)
async def get_celery_tasks(
    current_user: User = Depends(current_superuser),
    status: Optional[str] = Query(None, description="筛选状态: active, scheduled, reserved, all"),
    queue: Optional[str] = Query(None, description="筛选队列: default, all"),
    limit: int = Query(50, ge=1, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
):
    """
    获取 Celery 任务列表
    
    支持按状态和队列筛选，返回当前队列中的任务列表。
    只有超级管理员可以访问。
    
    Args:
        status: 筛选状态 (active, scheduled, reserved, all)
        queue: 筛选队列 (default, all)
        limit: 返回数量限制
        offset: 偏移量
        
    Returns:
        Celery 任务列表
    """
    logger.info(
        "celery_tasks_requested",
        admin_id=current_user.id,
        status=status,
        queue=queue,
        limit=limit,
        offset=offset,
    )
    
    try:
        # 获取 Inspector 实例
        inspect = celery_app.control.inspect()
        
        # 收集所有任务
        all_tasks: List[CeleryTaskInfo] = []
        
        # 并发查询不同状态的任务（带超时控制）
        query_tasks = []
        if status in [None, "all", "active"]:
            query_tasks.append(("active", run_celery_inspect_with_timeout(inspect.active)))
        if status in [None, "all", "scheduled"]:
            query_tasks.append(("scheduled", run_celery_inspect_with_timeout(inspect.scheduled)))
        if status in [None, "all", "reserved"]:
            query_tasks.append(("reserved", run_celery_inspect_with_timeout(inspect.reserved)))
        
        # 并发执行查询
        if query_tasks:
            results = await asyncio.gather(*[task[1] for task in query_tasks], return_exceptions=True)
            
            for i, (task_type, _) in enumerate(query_tasks):
                result = results[i]
                
                # 处理异常结果
                if isinstance(result, Exception):
                    logger.error(f"{task_type}_tasks_query_failed", error=str(result))
                    continue
                
                task_dict = result or {}
                
                # 提取任务信息
                if task_type == "active":
                    for worker_name, worker_tasks in task_dict.items():
                        for task_data in worker_tasks:
                            task_info = extract_task_info_from_active(task_data, worker_name)
                            all_tasks.append(task_info)
                elif task_type == "scheduled":
                    for worker_name, worker_tasks in task_dict.items():
                        for task_data in worker_tasks:
                            task_info = extract_task_info_from_scheduled(task_data, worker_name)
                            all_tasks.append(task_info)
                elif task_type == "reserved":
                    for worker_name, worker_tasks in task_dict.items():
                        for task_data in worker_tasks:
                            task_info = extract_task_info_from_reserved(task_data, worker_name)
                            all_tasks.append(task_info)
        
        # 按队列筛选
        if queue and queue != "all":
            all_tasks = [task for task in all_tasks if task.queue == queue]
        
        # 分页
        total = len(all_tasks)
        tasks = all_tasks[offset:offset + limit]
        
        logger.info(
            "celery_tasks_success",
            admin_id=current_user.id,
            total=total,
            returned=len(tasks),
        )
        
        return CeleryTaskListResponse(
            tasks=tasks,
            total=total,
        )
        
    except Exception as e:
        logger.error(
            "celery_tasks_failed",
            admin_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Celery tasks: {str(e)}"
        )


@router.get("/tasks/{task_id}", response_model=CeleryTaskInfo)
async def get_celery_task_detail(
    task_id: str,
    current_user: User = Depends(current_superuser),
):
    """
    获取单个 Celery 任务详情
    
    通过任务 ID 查询任务的详细信息，包括状态、结果、错误等。
    只有超级管理员可以访问。
    
    Args:
        task_id: 任务 ID
        
    Returns:
        Celery 任务详细信息
    """
    logger.info(
        "celery_task_detail_requested",
        admin_id=current_user.id,
        task_id=task_id,
    )
    
    try:
        task_info = get_task_result_info(task_id)
        
        logger.info(
            "celery_task_detail_success",
            admin_id=current_user.id,
            task_id=task_id,
            status=task_info.status,
        )
        
        return task_info
        
    except Exception as e:
        logger.error(
            "celery_task_detail_failed",
            admin_id=current_user.id,
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task detail: {str(e)}"
        )


@router.get("/workers", response_model=CeleryWorkerListResponse)
async def get_celery_workers(
    current_user: User = Depends(current_superuser),
):
    """
    获取 Celery Worker 列表
    
    返回当前活跃的 Worker 信息，包括主机名、状态、活跃任务数等。
    只有超级管理员可以访问。
    
    Returns:
        Celery Worker 列表
    """
    logger.info(
        "celery_workers_requested",
        admin_id=current_user.id,
    )
    
    try:
        # 获取 Inspector 实例
        inspect = celery_app.control.inspect()
        
        # 并发查询活跃任务和统计信息（带超时控制）
        active_tasks, stats = await asyncio.gather(
            run_celery_inspect_with_timeout(inspect.active),
            run_celery_inspect_with_timeout(inspect.stats),
            return_exceptions=True,
        )
        
        # 处理异常结果
        if isinstance(active_tasks, Exception):
            logger.error("active_tasks_query_failed", error=str(active_tasks))
            active_tasks = {}
        if isinstance(stats, Exception):
            logger.error("stats_query_failed", error=str(stats))
            stats = {}
        
        # 构建 Worker 列表
        workers: List[CeleryWorkerInfo] = []
        
        for worker_name in active_tasks.keys():
            worker_stats = stats.get(worker_name, {})
            
            worker_info = CeleryWorkerInfo(
                hostname=worker_name,
                status="online",
                active_tasks=len(active_tasks.get(worker_name, [])),
                processed_tasks=worker_stats.get("total", {}).get("tasks", 0) if worker_stats else None,
            )
            workers.append(worker_info)
        
        logger.info(
            "celery_workers_success",
            admin_id=current_user.id,
            total=len(workers),
        )
        
        return CeleryWorkerListResponse(
            workers=workers,
            total=len(workers),
        )
        
    except Exception as e:
        logger.error(
            "celery_workers_failed",
            admin_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Celery workers: {str(e)}"
        )


# ============================================================
# API 速率限制监控端点
# ============================================================

@router.get("/api-rate-limits", response_model=Dict[str, Any])
async def get_api_rate_limits(
    current_user: User = Depends(current_superuser),
):
    """
    获取所有API的速率限制使用情况
    
    返回各API Provider的当前速率使用情况，包括：
    - current_count: 当前1分钟窗口内的请求数
    - limit: 配置的速率限制（RPM）
    - usage_percent: 使用率百分比
    - available: 剩余可用次数
    
    只有超级管理员可以访问。
    
    Returns:
        所有Provider的速率使用情况
    """
    logger.info(
        "api_rate_limits_requested",
        admin_id=current_user.id,
    )
    
    try:
        rate_limiter = get_rate_limiter()
        usage_data = await rate_limiter.get_all_usage()
        stats_data = rate_limiter.get_stats()
        
        logger.info(
            "api_rate_limits_success",
            admin_id=current_user.id,
        )
        
        return {
            "usage": usage_data,
            "statistics": stats_data,
        }
        
    except Exception as e:
        logger.error(
            "api_rate_limits_failed",
            admin_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get API rate limits: {str(e)}"
        )


@router.get("/api-rate-limits/{provider}", response_model=Dict[str, Any])
async def get_api_rate_limit_by_provider(
    provider: str,
    current_user: User = Depends(current_superuser),
):
    """
    获取指定API Provider的速率限制使用情况
    
    Args:
        provider: API Provider名称（如openai, anthropic, deepseek, tavily）
        
    Returns:
        该Provider的速率使用情况
    """
    logger.info(
        "api_rate_limit_by_provider_requested",
        admin_id=current_user.id,
        provider=provider,
    )
    
    try:
        rate_limiter = get_rate_limiter()
        usage_data = await rate_limiter.get_current_usage(provider)
        
        logger.info(
            "api_rate_limit_by_provider_success",
            admin_id=current_user.id,
            provider=provider,
        )
        
        return usage_data
        
    except Exception as e:
        logger.error(
            "api_rate_limit_by_provider_failed",
            admin_id=current_user.id,
            provider=provider,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get API rate limit for {provider}: {str(e)}"
        )


@router.post("/api-rate-limits/{provider}/reset", response_model=Dict[str, Any])
async def reset_api_rate_limit(
    provider: str,
    current_user: User = Depends(current_superuser),
):
    """
    重置指定API Provider的速率限制（清空窗口记录）
    
    用于紧急情况下清空某个Provider的请求记录，重置速率限制。
    
    Args:
        provider: API Provider名称（如openai, anthropic, deepseek, tavily）
        
    Returns:
        操作结果
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
        
        logger.info(
            "api_rate_limit_reset_success",
            admin_id=current_user.id,
            provider=provider,
        )
        
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
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset API rate limit for {provider}: {str(e)}"
        )

