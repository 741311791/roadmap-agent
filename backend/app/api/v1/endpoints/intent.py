"""
需求分析元数据 API 端点

提供需求分析元数据的查询功能。

重构说明：
- ✅ Schema定义移到独立文件（app/schemas/intent.py）
- ✅ 使用CurrentSession（只读操作）
- ✅ 使用自定义异常替代HTTPException
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from fastapi import APIRouter
import structlog

from app.api.v1.deps import CurrentSession
from app.services.intent_service import IntentService
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.intent import IntentAnalysisResponse

router = APIRouter(prefix="/intent-analysis", tags=["intent-analysis"])
logger = structlog.get_logger()


@router.get("/{task_id}", response_model=ResponseSchemaModel[IntentAnalysisResponse])
async def get_intent_analysis(
    task_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
) -> ResponseSchemaModel[IntentAnalysisResponse]:
    """
    获取指定task_id的需求分析元数据
    
    用于查询路线图生成过程中的需求分析结果。
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        需求分析元数据
        
    Raises:
        NotFoundError: 需求分析元数据不存在
    """
    service = IntentService()
    metadata = await service.get_intent_analysis_metadata(db, task_id)
    
    if not metadata:
        raise errors.NotFoundError(msg="未找到需求分析元数据")
    
    return response_base.success(data=IntentAnalysisResponse(
        id=metadata.id,
        task_id=metadata.task_id,
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
