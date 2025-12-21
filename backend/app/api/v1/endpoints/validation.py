"""
结构验证记录相关端点

提供查询验证历史记录的 API。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import get_db
from app.db.repositories.validation_repo import ValidationRepository

router = APIRouter(prefix="/tasks", tags=["validation"])
logger = structlog.get_logger()


@router.get("/{task_id}/validation/latest")
async def get_latest_validation(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取任务的最新验证结果
    
    Args:
        task_id: 任务 ID
        db: 数据库会话
        
    Returns:
        最新的验证记录，包含验证结果、问题列表等
        
    Raises:
        HTTPException: 404 - 验证记录不存在
        
    Example:
        ```json
        {
            "id": "uuid",
            "task_id": "task-123",
            "roadmap_id": "roadmap-456",
            "is_valid": false,
            "overall_score": 75.5,
            "issues": {
                "issues": [
                    {
                        "severity": "critical",
                        "location": "Stage 2 > Module 1",
                        "issue": "循环依赖检测到",
                        "suggestion": "移除 Concept A -> B -> A 的依赖"
                    }
                ]
            },
            "validation_round": 1,
            "critical_count": 2,
            "warning_count": 5,
            "suggestion_count": 3,
            "created_at": "2024-01-01T00:00:00"
        }
        ```
    """
    repo = ValidationRepository(db)
    record = await repo.get_latest_by_task(task_id)
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"No validation record found for task {task_id}"
        )
    
    # 转换为字典并返回
    result = {
        "id": record.id,
        "task_id": record.task_id,
        "roadmap_id": record.roadmap_id,
        "is_valid": record.is_valid,
        "overall_score": record.overall_score,
        "issues": record.issues.get("issues", []) if isinstance(record.issues, dict) else record.issues,
        "dimension_scores": record.dimension_scores.get("scores", []) if isinstance(record.dimension_scores, dict) else record.dimension_scores,
        "improvement_suggestions": record.improvement_suggestions.get("suggestions", []) if isinstance(record.improvement_suggestions, dict) else record.improvement_suggestions,
        "validation_summary": record.validation_summary,
        "validation_round": record.validation_round,
        "critical_count": record.critical_count,
        "warning_count": record.warning_count,
        "suggestion_count": record.suggestion_count,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
    
    logger.info(
        "validation_record_retrieved",
        task_id=task_id,
        validation_round=record.validation_round,
    )
    
    return result


@router.get("/{task_id}/validation/history")
async def get_validation_history(
    task_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取任务的所有验证历史记录
    
    Args:
        task_id: 任务 ID
        db: 数据库会话
        
    Returns:
        验证记录列表（按轮次降序排列）
        
    Example:
        ```json
        [
            {
                "id": "uuid-1",
                "task_id": "task-123",
                "validation_round": 2,
                "is_valid": true,
                "overall_score": 92.0,
                "created_at": "2024-01-01T01:00:00"
            },
            {
                "id": "uuid-2",
                "task_id": "task-123",
                "validation_round": 1,
                "is_valid": false,
                "overall_score": 75.5,
                "created_at": "2024-01-01T00:00:00"
            }
        ]
        ```
    """
    repo = ValidationRepository(db)
    records = await repo.get_all_by_task(task_id)
    
    # 转换为字典列表
    result = []
    for record in records:
        result.append({
            "id": record.id,
            "task_id": record.task_id,
            "roadmap_id": record.roadmap_id,
            "is_valid": record.is_valid,
            "overall_score": record.overall_score,
            "issues": record.issues.get("issues", []) if isinstance(record.issues, dict) else record.issues,
            "dimension_scores": record.dimension_scores.get("scores", []) if isinstance(record.dimension_scores, dict) else record.dimension_scores,
            "improvement_suggestions": record.improvement_suggestions.get("suggestions", []) if isinstance(record.improvement_suggestions, dict) else record.improvement_suggestions,
            "validation_summary": record.validation_summary,
            "validation_round": record.validation_round,
            "critical_count": record.critical_count,
            "warning_count": record.warning_count,
            "suggestion_count": record.suggestion_count,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        })
    
    logger.info(
        "validation_history_retrieved",
        task_id=task_id,
        records_count=len(records),
    )
    
    return result





