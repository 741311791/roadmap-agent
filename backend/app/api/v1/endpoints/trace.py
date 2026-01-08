"""
执行日志追踪 API 端点

提供路线图生成过程的执行日志查询功能，用于调试和监控。

重构说明：
- ✅ Schema定义移到独立文件（app/schemas/trace.py）
- ✅ 使用CurrentSession（只读操作）
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from typing import Optional
from fastapi import APIRouter
import structlog

from app.api.v1.deps import CurrentSession
from app.services.trace_service import TraceService
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.trace import (
    ExecutionLogResponse,
    ExecutionLogListResponse,
    TraceSummaryResponse,
)

router = APIRouter(prefix="/trace", tags=["trace"])
logger = structlog.get_logger()


@router.get("/{task_id}/logs", response_model=ResponseSchemaModel[ExecutionLogListResponse])
async def get_logs(
    task_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
    level: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> ResponseSchemaModel[ExecutionLogListResponse]:
    """
    获取指定task_id的执行日志
    
    用于查询路线图生成过程的详细日志，支持按日志级别和分类过滤。
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        level: 日志级别筛选（可选）
        category: 日志分类筛选（可选）
        limit: 返回数量限制
        offset: 分页偏移
        
    Returns:
        日志列表和分页信息
    """
    logger.info(
        "get_logs_requested",
        task_id=task_id,
        level=level,
        category=category,
        limit=limit,
        offset=offset,
    )
    
    service = TraceService()
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
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
) -> ResponseSchemaModel[TraceSummaryResponse]:
    """
    获取执行日志摘要统计
    
    提供任务的整体日志统计信息，包括:
    - 日志级别分布
    - 日志分类分布
    - 总耗时
    - 时间范围
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        日志统计摘要
    """
    logger.info("get_summary_requested", task_id=task_id)
    
    service = TraceService()
    summary = await service.get_execution_logs_summary(db, task_id)
    
    return response_base.success(data=TraceSummaryResponse(**summary))


@router.get("/{task_id}/errors", response_model=ResponseSchemaModel[ExecutionLogListResponse])
async def get_errors(
    task_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
    limit: int = 50,
) -> ResponseSchemaModel[ExecutionLogListResponse]:
    """
    获取错误日志
    
    仅返回级别为error的日志，用于快速定位问题。
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        limit: 返回数量限制
        
    Returns:
        错误日志列表
    """
    logger.info("get_errors_requested", task_id=task_id, limit=limit)
    
    service = TraceService()
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
