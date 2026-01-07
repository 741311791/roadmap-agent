"""
编辑记录 API 端点

提供路线图编辑历史记录的查询功能。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import structlog

from app.db.session import get_db_transaction
from app.services.edit_service import EditService

router = APIRouter(prefix="/tasks", tags=["edit"])
logger = structlog.get_logger()


# ============================================================
# Pydantic 模型
# ============================================================

class EditRecordResponse(BaseModel):
    """编辑记录响应"""
    id: str
    task_id: str
    version: int
    edit_type: str
    human_feedback: Optional[str] = None
    modifications_count: int
    created_at: str


class EditRecordListResponse(BaseModel):
    """编辑记录列表响应"""
    records: list[EditRecordResponse]
    total: int


class RoadmapComparisonResponse(BaseModel):
    """路线图对比响应"""
    task_id: str
    current_version: int
    previous_version: int
    comparison: dict


# ============================================================
# 路由端点
# ============================================================

@router.get("/{task_id}/edit-records/latest", response_model=EditRecordResponse)
async def get_latest_edit_record(
    task_id: str,
    db: AsyncSession = Depends(get_db_transaction),
):
    """获取最新的编辑记录"""
    service = EditService()
    record = await service.get_latest_edit_record(db, task_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="No edit records found")
    
    return EditRecordResponse(
        id=record.id,
        task_id=record.task_id,
        version=record.version,
        edit_type=record.edit_type,
        human_feedback=record.human_feedback,
        modifications_count=len(record.modifications or []),
        created_at=record.created_at.isoformat(),
    )


@router.get("/{task_id}/edit-records", response_model=EditRecordListResponse)
async def get_all_edit_records(
    task_id: str,
    db: AsyncSession = Depends(get_db_transaction),
):
    """获取所有编辑记录"""
    service = EditService()
    records = await service.get_all_edit_records(db, task_id)
    
    record_responses = [
        EditRecordResponse(
            id=r.id,
            task_id=r.task_id,
            version=r.version,
            edit_type=r.edit_type,
            human_feedback=r.human_feedback,
            modifications_count=len(r.modifications or []),
            created_at=r.created_at.isoformat(),
        )
        for r in records
    ]
    
    return EditRecordListResponse(
        records=record_responses,
        total=len(record_responses),
    )


@router.get("/{task_id}/roadmap-comparison", response_model=RoadmapComparisonResponse)
async def get_roadmap_comparison(
    task_id: str,
    db: AsyncSession = Depends(get_db_transaction),
):
    """获取路线图版本对比"""
    service = EditService()
    comparison = await service.get_roadmap_comparison(db, task_id)
    
    if not comparison:
        raise HTTPException(
            status_code=404,
            detail="No comparison available (need at least 2 versions)"
        )
    
    return RoadmapComparisonResponse(
        task_id=task_id,
        current_version=comparison.get("current_version", 0),
        previous_version=comparison.get("previous_version", 0),
        comparison=comparison,
    )
