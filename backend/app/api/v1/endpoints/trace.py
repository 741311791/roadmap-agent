"""
执行日志追踪 API 端点

提供路线图生成过程的执行日志查询功能，用于调试和监控。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import structlog

from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository

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
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定 task_id 的执行日志
    
    用于查询路线图生成过程的详细日志，支持按日志级别和分类过滤。
    
    Args:
        task_id: 追踪 ID（通常等于 task_id）
        level: 过滤日志级别（可选）：debug, info, warning, error
        category: 过滤日志分类（可选）：workflow, agent, tool, database
        limit: 返回数量限制（默认 100，最大 2000）
        offset: 分页偏移（默认 0）
        db: 数据库会话
        
    Returns:
        执行日志列表，按时间顺序排列
        
    Example:
        ```json
        {
            "logs": [
                {
                    "id": "log-123",
                    "task_id": "550e8400-e29b-41d4-a716-446655440000",
                    "roadmap_id": "python-guide-xxx",
                    "concept_id": "concept-456",
                    "level": "info",
                    "category": "agent",
                    "step": "tutorial_generation",
                    "agent_name": "TutorialGeneratorAgent",
                    "message": "Tutorial generation started",
                    "details": {
                        "concept_name": "Introduction to Python"
                    },
                    "duration_ms": 1500,
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ],
            "total": 150,
            "offset": 0,
            "limit": 100
        }
        ```
    """
    # 限制最大返回数量（提高到 2000 以支持前端按 step 分组）
    limit = min(limit, 2000)
    
    repo = RoadmapRepository(db)
    
    # 获取总数和日志列表
    total = await repo.count_execution_logs_by_trace(
        task_id=task_id,
        level=level,
        category=category,
    )
    
    logs = await repo.get_execution_logs_by_trace(
        task_id=task_id,
        level=level,
        category=category,
        limit=limit,
        offset=offset,
    )
    
    return ExecutionLogListResponse(
        logs=[
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
                created_at=log.created_at.isoformat() if log.created_at else "",
            )
            for log in logs
        ],
        total=total,  # 使用实际的总记录数
        offset=offset,
        limit=limit,
    )


@router.get("/{task_id}/summary", response_model=TraceSummaryResponse)
async def get_summary(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定 task_id 的执行摘要
    
    提供路线图生成过程的统计摘要，包括日志级别分布、分类统计、总耗时等。
    
    Args:
        task_id: 追踪 ID
        db: 数据库会话
        
    Returns:
        执行摘要统计，包含：
        - level_stats: 各日志级别的数量统计
        - category_stats: 各分类的数量统计
        - total_duration_ms: 总耗时（毫秒）
        - first_log_at: 首次日志时间
        - last_log_at: 最后日志时间
        - total_logs: 总日志数
        
    Example:
        ```json
        {
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "level_stats": {
                "info": 100,
                "warning": 5,
                "error": 2,
                "debug": 50
            },
            "category_stats": {
                "workflow": 20,
                "agent": 100,
                "tool": 30,
                "database": 7
            },
            "total_duration_ms": 45000,
            "first_log_at": "2024-01-01T00:00:00Z",
            "last_log_at": "2024-01-01T00:00:45Z",
            "total_logs": 157
        }
        ```
    """
    repo = RoadmapRepository(db)
    summary = await repo.get_execution_logs_summary(task_id)
    
    return TraceSummaryResponse(**summary)


@router.get("/{task_id}/errors", response_model=ExecutionLogListResponse)
async def get_errors(
    task_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定 task_id 的错误日志
    
    快速查询路线图生成过程中的所有错误日志，用于问题诊断。
    
    Args:
        task_id: 追踪 ID
        limit: 返回数量限制（默认 50）
        db: 数据库会话
        
    Returns:
        错误日志列表，按时间降序排列
        
    Example:
        ```json
        {
            "logs": [
                {
                    "id": "log-error-123",
                    "task_id": "550e8400-e29b-41d4-a716-446655440000",
                    "roadmap_id": "python-guide-xxx",
                    "level": "error",
                    "category": "agent",
                    "step": "tutorial_generation",
                    "agent_name": "TutorialGeneratorAgent",
                    "message": "Failed to generate tutorial",
                    "details": {
                        "error_type": "TimeoutError",
                        "concept_id": "concept-456"
                    },
                    "created_at": "2024-01-01T00:00:30Z"
                }
            ],
            "total": 2,
            "offset": 0,
            "limit": 50
        }
        ```
    """
    repo = RoadmapRepository(db)
    logs = await repo.get_error_logs_by_trace(task_id, limit=limit)
    
    return ExecutionLogListResponse(
        logs=[
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
                created_at=log.created_at.isoformat() if log.created_at else "",
            )
            for log in logs
        ],
        total=len(logs),
        offset=0,
        limit=limit,
    )
