"""
验证记录 API 端点

提供路线图验证历史记录的查询功能。

重构说明：
- ✅ Schema定义移到独立文件（app/schemas/validation.py）
- ✅ 使用CurrentSession（只读操作）
- ✅ 使用自定义异常替代HTTPException
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from fastapi import APIRouter
import structlog

from app.api.v1.deps import CurrentSession
from app.services.validation_service import ValidationService
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.validation import (
    ValidationRecordResponse,
    ValidationRecordListResponse,
)

router = APIRouter(prefix="/tasks", tags=["validation"])
logger = structlog.get_logger()


@router.get("/{task_id}/validation-records/latest", response_model=ResponseSchemaModel[ValidationRecordResponse])
async def get_latest_validation_record(
    task_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
) -> ResponseSchemaModel[ValidationRecordResponse]:
    """
    获取最新的验证记录
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        最新版本的验证记录
        
    Raises:
        NotFoundError: 没有找到验证记录
    """
    service = ValidationService()
    record = await service.get_latest_validation_record(db, task_id)
    
    if not record:
        raise errors.NotFoundError(msg="未找到验证记录")
    
    return response_base.success(data=ValidationRecordResponse(
        id=record.id,
        task_id=record.task_id,
        version=record.version,
        validation_status=record.validation_status,
        issues_found=len(record.issues or []),
        issues_details=record.issues,
        suggestions=record.suggestions,
        created_at=record.created_at.isoformat(),
    ))


@router.get("/{task_id}/validation-records", response_model=ResponseSchemaModel[ValidationRecordListResponse])
async def get_all_validation_records(
    task_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
) -> ResponseSchemaModel[ValidationRecordListResponse]:
    """
    获取所有验证记录
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        验证记录列表（按版本号降序）
    """
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
    
    return response_base.success(data=ValidationRecordListResponse(
        records=record_responses,
        total=len(record_responses),
    ))
