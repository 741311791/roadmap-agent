"""
验证记录 API 端点

提供路线图验证历史记录的查询功能。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import structlog

from app.db.session import get_db_transaction
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/tasks", tags=["validation"])
logger = structlog.get_logger()


# ============================================================
# Pydantic 模型
# ============================================================

class ValidationRecordResponse(BaseModel):
    """验证记录响应"""
    id: str
    task_id: str
    version: int
    validation_status: str
    issues_found: int
    issues_details: Optional[list] = None
    suggestions: Optional[list] = None
    created_at: str


class ValidationRecordListResponse(BaseModel):
    """验证记录列表响应"""
    records: list[ValidationRecordResponse]
    total: int


# ============================================================
# 路由端点
# ============================================================

@router.get("/{task_id}/validation-records/latest", response_model=ValidationRecordResponse)
async def get_latest_validation_record(
    task_id: str,
    db: AsyncSession = Depends(get_db_transaction),
):
    """获取最新的验证记录"""
    service = ValidationService()
    record = await service.get_latest_validation_record(db, task_id)
    
    if not record:
        raise HTTPException(status_code=404, detail="No validation records found")
    
    return ValidationRecordResponse(
        id=record.id,
        task_id=record.task_id,
        version=record.version,
        validation_status=record.validation_status,
        issues_found=len(record.issues or []),
        issues_details=record.issues,
        suggestions=record.suggestions,
        created_at=record.created_at.isoformat(),
    )


@router.get("/{task_id}/validation-records", response_model=ValidationRecordListResponse)
async def get_all_validation_records(
    task_id: str,
    db: AsyncSession = Depends(get_db_transaction),
):
    """获取所有验证记录"""
    service = ValidationService()
    records = await service.get_all_validation_records(db, task_id)
    
    record_responses = [
        ValidationRecordResponse(
            id=r.id,
            task_id=r.task_id,
            version=r.version,
            validation_status=r.validation_status,
            issues_found=len(r.issues or []),
            issues_details=r.issues,
            suggestions=r.suggestions,
            created_at=r.created_at.isoformat(),
        )
        for r in records
    ]
    
    return ValidationRecordListResponse(
        records=record_responses,
        total=len(record_responses),
    )
