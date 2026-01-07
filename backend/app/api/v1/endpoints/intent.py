"""
需求分析元数据 API 端点

提供需求分析元数据的查询功能。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import structlog

from app.db.session import get_db_transaction
from app.services.intent_service import IntentService

router = APIRouter(prefix="/intent-analysis", tags=["intent-analysis"])
logger = structlog.get_logger()


# ============================================================
# Pydantic 模型
# ============================================================

class IntentAnalysisResponse(BaseModel):
    """需求分析响应"""
    id: str
    task_id: str
    roadmap_id: Optional[str] = None
    parsed_goal: str
    key_technologies: list[str]
    difficulty_profile: str
    time_constraint: str
    recommended_focus: list[str]
    user_profile_summary: Optional[str] = None
    skill_gap_analysis: list[str]
    personalized_suggestions: list[str]
    estimated_learning_path_type: Optional[str] = None
    content_format_weights: Optional[dict] = None
    language_preferences: Optional[dict] = None
    created_at: Optional[str] = None


# ============================================================
# 路由端点
# ============================================================

@router.get("/{task_id}", response_model=IntentAnalysisResponse)
async def get_intent_analysis(
    task_id: str,
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    获取指定task_id的需求分析元数据
    
    用于查询路线图生成过程中的需求分析结果。
    """
    service = IntentService()
    metadata = await service.get_intent_analysis_metadata(db, task_id)
    
    if not metadata:
        raise HTTPException(status_code=404, detail="Intent analysis metadata not found")
    
    return IntentAnalysisResponse(
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
    )
