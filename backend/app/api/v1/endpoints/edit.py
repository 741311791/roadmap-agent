"""
编辑记录 API 端点

提供路线图编辑历史记录的查询功能。

重构说明：
- ✅ Schema定义移到独立文件（app/schemas/edit.py）
- ✅ 使用CurrentSession（只读操作）
- ✅ 使用自定义异常替代HTTPException
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from fastapi import APIRouter
import structlog

from app.api.v1.deps import CurrentSession
from app.services.edit_service import EditService
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.edit import (
    EditRecordResponse,
    EditRecordListResponse,
    RoadmapComparisonResponse,
)

router = APIRouter(prefix="/tasks", tags=["edit"])
logger = structlog.get_logger()


@router.get("/{task_id}/edit-records/latest", response_model=ResponseSchemaModel[EditRecordResponse])
async def get_latest_edit_record(
    task_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
) -> ResponseSchemaModel[EditRecordResponse]:
    """
    获取最新的编辑记录
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        最新版本的编辑记录
        
    Raises:
        NotFoundError: 没有找到编辑记录
    """
    service = EditService()
    record = await service.get_latest_edit_record(db, task_id)
    
    if not record:
        raise errors.NotFoundError(msg="未找到编辑记录")
    
    return response_base.success(data=EditRecordResponse(
        id=record.id,
        task_id=record.task_id,
        version=record.version,
        edit_type=record.edit_type,
        human_feedback=record.human_feedback,
        modifications_count=len(record.modifications or []),
        created_at=record.created_at.isoformat(),
    ))


@router.get("/{task_id}/edit-records", response_model=ResponseSchemaModel[EditRecordListResponse])
async def get_all_edit_records(
    task_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
) -> ResponseSchemaModel[EditRecordListResponse]:
    """
    获取所有编辑记录
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        编辑记录列表（按版本号降序）
    """
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
    
    return response_base.success(data=EditRecordListResponse(
        records=record_responses,
        total=len(record_responses),
    ))


@router.get("/{task_id}/roadmap-comparison", response_model=ResponseSchemaModel[RoadmapComparisonResponse])
async def get_roadmap_comparison(
    task_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
) -> ResponseSchemaModel[RoadmapComparisonResponse]:
    """
    获取路线图版本对比
    
    对比当前版本与前一版本的差异。
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        版本对比详情
        
    Raises:
        NotFoundError: 没有足够的版本进行对比（至少需要2个版本）
    """
    service = EditService()
    comparison = await service.get_roadmap_comparison(db, task_id)
    
    if not comparison:
        raise errors.NotFoundError(msg="没有足够的版本进行对比（至少需要2个版本）")
    
    return response_base.success(data=RoadmapComparisonResponse(
        task_id=task_id,
        current_version=comparison.get("current_version", 0),
        previous_version=comparison.get("previous_version", 0),
        comparison=comparison,
    ))
