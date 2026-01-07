"""
执行日志追踪 API 端点

提供路线图生成过程的执行日志查询功能，用于调试和监控。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import structlog

from app.db.session import get_db_readonly
from app.services.trace_service import TraceService

router = APIRouter(prefix="/trace", tags=["trace"])
logger = structlog.get_logger()


# ============================================================
# Pydantic 模型
# ============================================================

class ExecutionLogResponse(BaseModel):
    """执行日志响应"""
    id: str
    task_id: str
    roadmap_id: Optional[str] = None
    concept_id: Optional[str] = None
    level: str
    category: str
    step: Optional[str] = None
    agent_name: Optional[str] = None
    message: str
    details: Optional[dict] = None
    duration_ms: Optional[int] = None
    created_at: str


class ExecutionLogListResponse(BaseModel):
    """执行日志列表响应"""
    logs: list[ExecutionLogResponse]
    total: int
    offset: int
    limit: int


class TraceSummaryResponse(BaseModel):
    """追踪摘要响应"""
    task_id: str
    level_stats: dict[str, int]
    category_stats: dict[str, int]
    total_duration_ms: int
    first_log_at: Optional[str] = None
    last_log_at: Optional[str] = None
    total_logs: int


# ============================================================
# 路由端点
# ============================================================

@router.get("/{task_id}/logs", response_model=ExecutionLogListResponse)
async def get_logs(
    task_id: str,
    level: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_readonly),
):
    """
    获取指定task_id的执行日志
    
    用于查询路线图生成过程的详细日志，支持按日志级别和分类过滤。
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
    
    return ExecutionLogListResponse(
        logs=log_responses,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{task_id}/summary", response_model=TraceSummaryResponse)
async def get_summary(
    task_id: str,
    db: AsyncSession = Depends(get_db_readonly),
):
    """
    获取执行日志摘要统计
    
    提供任务的整体日志统计信息，包括:
    - 日志级别分布
    - 日志分类分布
    - 总耗时
    - 时间范围
    """
    logger.info("get_summary_requested", task_id=task_id)
    
    service = TraceService()
    summary = await service.get_execution_logs_summary(db, task_id)
    
    return TraceSummaryResponse(**summary)


@router.get("/{task_id}/errors", response_model=ExecutionLogListResponse)
async def get_errors(
    task_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_readonly),
):
    """
    获取错误日志
    
    仅返回级别为error的日志，用于快速定位问题。
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
    
    return ExecutionLogListResponse(
        logs=log_responses,
        total=len(log_responses),
        offset=0,
        limit=limit,
    )
