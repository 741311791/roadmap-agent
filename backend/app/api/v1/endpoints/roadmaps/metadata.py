"""
路线图元数据查询 API 端点

提供需求分析、编辑记录、验证记录等元数据的查询功能。

重构变更：
- ✅ 合并多个文件的元数据查询接口：
  - roadmaps/intent.py: 需求分析元数据
  - roadmaps/edit.py: 编辑记录
  - roadmaps/validation.py: 验证记录
- ✅ 统一到 /roadmaps prefix
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from fastapi import APIRouter
import structlog

from app.api.v1.deps import CurrentSession
from app.services.roadmaps.intent_service import IntentService
from app.services.roadmaps.edit_service import EditService
from app.services.roadmaps.validation_service import ValidationService
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.intent import IntentAnalysisResponse
from app.schemas.edit import (
    EditRecordResponse,
    EditRecordListResponse,
    RoadmapComparisonResponse,
)
from app.schemas.validation import (
    ValidationRecordResponse,
    ValidationRecordListResponse,
)

router = APIRouter(prefix="/roadmaps", tags=["roadmap-metadata"])
logger = structlog.get_logger()


# ============================================================
# 需求分析元数据
# ============================================================

@router.get("/{roadmap_id}/intent-analysis", response_model=ResponseSchemaModel[IntentAnalysisResponse])
async def get_intent_analysis(
    roadmap_id: str,
    db: CurrentSession,
) -> ResponseSchemaModel[IntentAnalysisResponse]:
    """
    获取指定路线图的需求分析元数据
    
    状态处理：
    - 数据已生成: 返回完整数据
    - 任务执行中: 返回任务状态 (available=False)
    - 任务不存在: 返回 404
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
        
    Returns:
        需求分析元数据或任务状态
        
    Raises:
        NotFoundError: 需求分析元数据不存在
    """
    service = IntentService()
    metadata = await service.get_intent_analysis_metadata(db, roadmap_id)
    
    if metadata:
        # ✅ 数据已生成，返回完整数据
        return response_base.success(data=IntentAnalysisResponse(
            available=True,
            intent_id=metadata.intent_id,
            roadmap_id=metadata.roadmap_id,
            parsed_goal=metadata.parsed_goal,
            key_technologies=metadata.key_technologies,
            difficulty_profile=metadata.difficulty_profile,
            time_constraint=metadata.time_constraint,
            recommended_focus=metadata.recommended_focus,
            user_profile_summary=metadata.user_profile_summary,
            skill_gap_analysis=metadata.skill_gap_analysis,
            personalized_suggestions=metadata.personalized_suggestions,
            estimated_learning_path_type=metadata.estimated_learning_path_type,
            content_format_weights=metadata.content_format_weights,
            language_preferences=metadata.language_preferences,
            created_at=metadata.created_at.isoformat() if metadata.created_at else None,
        ))
    
    # ✅ 数据不存在，检查是否有活跃任务
    from app.crud.crud_task import get_task_crud
    task_crud = get_task_crud()
    active_task = await task_crud.get_latest_by_roadmap_id(db, roadmap_id)
    
    if active_task and active_task.status in ["pending", "processing"]:
        # ✅ 任务执行中，返回友好的"未就绪"状态
        return response_base.success(data=IntentAnalysisResponse(
            available=False,
            status=active_task.status,
            current_step=active_task.current_step,
            message="需求分析正在进行中，请稍后查询",
        ))
    
    # ✅ 任务不存在或已完成但数据缺失
    if active_task and active_task.status == "completed":
        # 数据应该存在但实际缺失，这是严重问题
        logger.error(
            "intent_analysis_missing_after_completion",
            roadmap_id=roadmap_id,
            task_id=active_task.task_id,
        )
    
    raise errors.NotFoundError(msg="未找到需求分析元数据")


# ============================================================
# 编辑记录
# ============================================================

@router.get("/{roadmap_id}/edit-records/latest", response_model=ResponseSchemaModel[EditRecordResponse])
async def get_latest_edit_record(
    roadmap_id: str,
    db: CurrentSession,
) -> ResponseSchemaModel[EditRecordResponse]:
    """
    获取最新的编辑记录
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
        
    Returns:
        最新版本的编辑记录
        
    Raises:
        NotFoundError: 没有找到编辑记录
    """
    service = EditService()
    record = await service.get_latest_edit_record_by_roadmap(db, roadmap_id)
    
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


@router.get("/{roadmap_id}/edit-records", response_model=ResponseSchemaModel[EditRecordListResponse])
async def get_all_edit_records(
    roadmap_id: str,
    db: CurrentSession,
) -> ResponseSchemaModel[EditRecordListResponse]:
    """
    获取所有编辑记录
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
        
    Returns:
        编辑记录列表（按版本号降序）
    """
    service = EditService()
    records = await service.get_all_edit_records_by_roadmap(db, roadmap_id)
    
    record_responses = [
        EditRecordResponse(
            id=r.id,
            task_id=r.task_id,
            version=r.edit_round,
            edit_type="unknown",
            human_feedback=None,
            modifications_count=len(r.modified_node_ids or []),
            created_at=r.created_at.isoformat(),
        )
        for r in records
    ]
    
    return response_base.success(data=EditRecordListResponse(
        records=record_responses,
        total=len(record_responses),
    ))


@router.get("/{roadmap_id}/comparison", response_model=ResponseSchemaModel[RoadmapComparisonResponse])
async def get_roadmap_comparison(
    roadmap_id: str,
    db: CurrentSession,
) -> ResponseSchemaModel[RoadmapComparisonResponse]:
    """
    获取路线图版本对比
    
    对比当前版本与前一版本的差异。
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
        
    Returns:
        版本对比详情
        
    Raises:
        NotFoundError: 没有足够的版本进行对比（至少需要2个版本）
    """
    service = EditService()
    comparison = await service.get_roadmap_comparison_by_roadmap(db, roadmap_id)
    
    if not comparison:
        raise errors.NotFoundError(msg="没有足够的版本进行对比（至少需要2个版本）")
    
    return response_base.success(data=RoadmapComparisonResponse(
        roadmap_id=roadmap_id,
        current_version=comparison.get("current_version", 0),
        previous_version=comparison.get("previous_version", 0),
        comparison=comparison,
    ))


# ============================================================
# 验证记录
# ============================================================

@router.get("/{roadmap_id}/validation-records/latest", response_model=ResponseSchemaModel[ValidationRecordResponse])
async def get_latest_validation_record(
    roadmap_id: str,
    db: CurrentSession,
) -> ResponseSchemaModel[ValidationRecordResponse]:
    """
    获取最新的验证记录
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
        
    Returns:
        最新版本的验证记录
        
    Raises:
        NotFoundError: 没有找到验证记录
    """
    service = ValidationService()
    record = await service.get_latest_validation_record_by_roadmap(db, roadmap_id)
    
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


@router.get("/{roadmap_id}/validation-records", response_model=ResponseSchemaModel[ValidationRecordListResponse])
async def get_all_validation_records(
    roadmap_id: str,
    db: CurrentSession,
) -> ResponseSchemaModel[ValidationRecordListResponse]:
    """
    获取所有验证记录
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
        
    Returns:
        验证记录列表（按版本号降序）
    """
    service = ValidationService()
    records = await service.get_all_validation_records_by_roadmap(db, roadmap_id)
    
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


# ============================================================
# 编辑历史完整查询（包含diff详情）
# ============================================================

@router.get("/{roadmap_id}/edit/history-full", response_model=ResponseSchemaModel)
async def get_edit_history_full(
    roadmap_id: str,
    db: CurrentSession,
) -> ResponseSchemaModel:
    """
    获取完整编辑历史（包含详细diff和修改内容）
    
    返回路线图的所有编辑记录，包括：
    - 编辑来源（validation失败/人工反馈）
    - 修改内容详情
    - diff摘要
    - 关联的编辑计划
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
        
    Returns:
        完整编辑历史列表（按时间倒序）
        
    Example:
        {
            "success": true,
            "data": {
                "roadmap_id": "xxx",
                "edit_history": [
                    {
                        "id": 1,
                        "timestamp": "2026-01-23T12:00:00Z",
                        "edit_source": "validation_failed",
                        "edit_plan_id": "xxx",
                        "changes_made": {...},
                        "diff_summary": "修改了3个模块...",
                        "version": 2
                    }
                ],
                "total": 3
            }
        }
    """
    from app.crud.crud_edit import get_edit_crud
    from app.crud.crud_edit_plan import get_edit_plan_crud
    
    edit_crud = get_edit_crud()
    edit_plan_crud = get_edit_plan_crud()
    
    # 获取所有编辑记录
    edits = await edit_crud.get_by_roadmap_id(db, roadmap_id, limit=100)
    
    if not edits:
        logger.info("no_edit_history_found", roadmap_id=roadmap_id)
        return response_base.success(data={
            "roadmap_id": roadmap_id,
            "versions": [],
            "current_version": 0,
            "total": 0,
        })
    
    # 构建前端期望的 EditHistoryVersion 格式
    # 编辑记录按时间升序排列，version 从 1 开始递增
    versions = []
    for idx, edit in enumerate(reversed(edits), start=1):
        version_data = {
            "version": idx,
            "framework_data": edit.modified_framework_data,
            "created_at": edit.created_at.isoformat() if edit.created_at else None,
            "edit_round": edit.edit_round,
            "modification_summary": edit.modification_summary or "",
            "modified_node_ids": edit.modified_node_ids or [],
        }
        versions.append(version_data)
    
    logger.info(
        "edit_history_retrieved",
        roadmap_id=roadmap_id,
        total=len(versions)
    )
    
    return response_base.success(data={
        "roadmap_id": roadmap_id,
        "versions": versions,
        "current_version": len(versions),
        "total": len(versions),
    })

