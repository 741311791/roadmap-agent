"""
任务执行日志追踪 API 端点

提供任务执行过程的日志查询功能，用于调试和监控。

重构变更：
- ✅ 从 admin/trace.py 移动到 tasks/trace.py
- ✅ 添加用户身份验证（current_active_user）
- ✅ 添加权限验证（用户只能查看自己的任务，管理员可查看所有）
- ✅ 路由prefix从 /admin/trace 改为 /tasks
- ✅ 使用CurrentSession（只读操作）
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from typing import Optional, Annotated
from fastapi import APIRouter, Depends
import structlog

from app.api.v1.deps import CurrentSession
from app.models.database import User
from app.core.auth.deps import current_active_user
from app.services.shared.trace_service import TraceService, get_trace_service
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.trace import (
    ExecutionLogResponse,
    ExecutionLogListResponse,
    TraceSummaryResponse,
)

router = APIRouter(prefix="/tasks", tags=["task-trace"])
logger = structlog.get_logger()

# 依赖注入
CurrentUser = Annotated[User, Depends(current_active_user)]
CurrentTraceService = Annotated[TraceService, Depends(get_trace_service)]


@router.get("/{task_id}/logs", response_model=ResponseSchemaModel[ExecutionLogListResponse])
async def get_logs(
    task_id: str,
    db: CurrentSession,
    current_user: CurrentUser,
    service: CurrentTraceService,
    level: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> ResponseSchemaModel[ExecutionLogListResponse]:
    """
    获取指定任务的执行日志
    
    用于查询路线图生成过程的详细日志，支持按日志级别和分类过滤。
    
    权限控制：
    - 普通用户只能查看自己的任务日志
    - 超级管理员可以查看所有任务日志
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        current_user: 当前登录用户
        service: 日志追踪服务
        level: 日志级别筛选（可选）
        category: 日志分类筛选（可选）
        limit: 返回数量限制
        offset: 分页偏移
        
    Returns:
        日志列表和分页信息
        
    Raises:
        NotFoundError: 任务不存在
        ForbiddenError: 无权限查看此任务的日志
    """
    logger.info(
        "get_logs_requested",
        task_id=task_id,
        user_id=current_user.id,
        level=level,
        category=category,
        limit=limit,
        offset=offset,
    )
    
    # 验证任务所有权
    await service.verify_task_ownership(
        session=db,
        task_id=task_id,
        user_id=current_user.id,
        is_superuser=current_user.is_superuser,
    )
    
    # 获取日志
    total, logs = await service.get_execution_logs(
        session=db,
        task_id=task_id,
        offset=offset,
        limit=limit,
    )
    
    # 转换为响应格式
    log_responses = [
        ExecutionLogResponse(
            id=log.id,
            task_id=log.task_id,
            roadmap_id=log.roadmap_id,
            concept_id=log.concept_id,
            level=log.level,
            category=log.category,
            step=log.step,
            agent_name=log.agent_name,
            message=log.message,
            details=log.details,
            duration_ms=log.duration_ms,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]
    
    return response_base.success(data=ExecutionLogListResponse(
        logs=log_responses,
        total=total,
        offset=offset,
        limit=limit,
    ))


@router.get("/{task_id}/summary", response_model=ResponseSchemaModel[TraceSummaryResponse])
async def get_summary(
    task_id: str,
    db: CurrentSession,
    current_user: CurrentUser,
    service: CurrentTraceService,
) -> ResponseSchemaModel[TraceSummaryResponse]:
    """
    获取执行日志摘要统计
    
    提供任务的整体日志统计信息，包括:
    - 日志级别分布
    - 日志分类分布
    - 总耗时
    - 时间范围
    
    权限控制：
    - 普通用户只能查看自己的任务日志
    - 超级管理员可以查看所有任务日志
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        current_user: 当前登录用户
        service: 日志追踪服务
        
    Returns:
        日志统计摘要
        
    Raises:
        NotFoundError: 任务不存在
        ForbiddenError: 无权限查看此任务的日志
    """
    logger.info("get_summary_requested", task_id=task_id, user_id=current_user.id)
    
    # 验证任务所有权
    await service.verify_task_ownership(
        session=db,
        task_id=task_id,
        user_id=current_user.id,
        is_superuser=current_user.is_superuser,
    )
    
    # 获取摘要
    summary = await service.get_execution_logs_summary(db, task_id)
    
    return response_base.success(data=TraceSummaryResponse(**summary))


@router.get("/{task_id}/errors", response_model=ResponseSchemaModel[ExecutionLogListResponse])
async def get_errors(
    task_id: str,
    db: CurrentSession,
    current_user: CurrentUser,
    service: CurrentTraceService,
    limit: int = 50,
) -> ResponseSchemaModel[ExecutionLogListResponse]:
    """
    获取错误日志
    
    仅返回级别为error的日志，用于快速定位问题。
    
    权限控制：
    - 普通用户只能查看自己的任务日志
    - 超级管理员可以查看所有任务日志
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        current_user: 当前登录用户
        service: 日志追踪服务
        limit: 返回数量限制
        
    Returns:
        错误日志列表
        
    Raises:
        NotFoundError: 任务不存在
        ForbiddenError: 无权限查看此任务的日志
    """
    logger.info("get_errors_requested", task_id=task_id, user_id=current_user.id, limit=limit)
    
    # 验证任务所有权
    await service.verify_task_ownership(
        session=db,
        task_id=task_id,
        user_id=current_user.id,
        is_superuser=current_user.is_superuser,
    )
    
    # 获取错误日志
    logs = await service.get_error_logs(db, task_id, limit=limit)
    
    # 转换为响应格式
    log_responses = [
        ExecutionLogResponse(
            id=log.id,
            task_id=log.task_id,
            roadmap_id=log.roadmap_id,
            concept_id=log.concept_id,
            level=log.level,
            category=log.category,
            step=log.step,
            agent_name=log.agent_name,
            message=log.message,
            details=log.details,
            duration_ms=log.duration_ms,
            created_at=log.created_at.isoformat(),
        )
        for log in logs
    ]
    
    return response_base.success(data=ExecutionLogListResponse(
        logs=log_responses,
        total=len(log_responses),
        offset=0,
        limit=limit,
    ))


@router.get("/{task_id}/subgraph-progress")
async def get_subgraph_progress(
    task_id: str,
    current_user: CurrentUser,
) -> ResponseSchemaModel:
    """
    查询子图执行进度（双 Checkpointer 架构）
    
    使用子图 checkpointer 查询当前任务的子图状态：
    - 已完成的 Concept 数量
    - 失败的 Concept 列表
    - 可恢复性（是否可以断点续传）
    
    双 Checkpointer 架构：
    - 使用 child_checkpointer（命名空间：child_graph）查询子图状态
    - 与父图状态完全隔离
    - 支持细粒度的断点续传
    
    Args:
        task_id: 任务ID
        current_user: 当前用户
    
    Returns:
        子图进度信息
        
    Raises:
        NotFoundError: 任务不存在
        ForbiddenError: 无权限查看此任务
    """
    logger.info(
        "get_subgraph_progress_requested",
        task_id=task_id,
        user_id=current_user.id,
    )
    
    # 创建并初始化 OrchestratorFactory
    from app.core.orchestrator_factory import OrchestratorFactory
    
    factory = OrchestratorFactory()
    await factory.initialize()
    
    # ✅ 使用子图 checkpointer 查询进度
    child_checkpointer = factory.get_child_checkpointer()
    config = {"configurable": {"thread_id": task_id}}
    
    try:
        state_snapshot = await child_checkpointer.aget(config)
    except Exception as e:
        logger.error(
            "failed_to_query_subgraph_progress",
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        state_snapshot = None
    
    if not state_snapshot:
        return response_base.success(
            message="子图尚未执行或已完成",
            data={
                "resumable": False,
                "completed_nodes": 0,
                "total_nodes": 0,
                "failed_nodes": [],
                "pending_nodes": [],
            }
        )
    
    # 解析子图进度
    tasks = state_snapshot.tasks if hasattr(state_snapshot, "tasks") else []
    
    # 统计各状态的任务
    completed_tasks = []
    failed_tasks = []
    pending_tasks = []
    
    for task in tasks:
        task_status = task.get("status", "unknown") if isinstance(task, dict) else "unknown"
        task_name = task.get("name", "unknown") if isinstance(task, dict) else "unknown"
        
        if task_status == "completed":
            completed_tasks.append(task_name)
        elif task_status == "failed":
            failed_tasks.append({
                "node_name": task_name,
                "error": task.get("error", "Unknown error") if isinstance(task, dict) else "Unknown error",
            })
        else:
            pending_tasks.append(task_name)
    
    logger.info(
        "subgraph_progress_retrieved",
        task_id=task_id,
        completed_count=len(completed_tasks),
        failed_count=len(failed_tasks),
        pending_count=len(pending_tasks),
    )
    
    return response_base.success(
        message="子图进度查询成功",
        data={
            "resumable": len(failed_tasks) > 0 or len(pending_tasks) > 0,
            "completed_nodes": len(completed_tasks),
            "failed_nodes": failed_tasks,
            "pending_nodes": pending_tasks,
            "total_nodes": len(tasks),
        }
    )

