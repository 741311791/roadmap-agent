"""
需求分析元数据 API 端点

提供需求分析元数据的查询功能。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import structlog

from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository

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
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定 task_id 的需求分析元数据
    
    用于查询路线图生成过程中的需求分析结果，包含技术栈分析、学习路径类型、
    个性化建议等信息。
    
    Args:
        task_id: 任务 ID
        db: 数据库会话
        
    Returns:
        需求分析元数据，包含：
        - parsed_goal: 解析后的学习目标
        - key_technologies: 关键技术列表
        - difficulty_profile: 难度概况
        - time_constraint: 时间约束
        - recommended_focus: 推荐关注点
        - skill_gap_analysis: 技能差距分析
        - personalized_suggestions: 个性化建议
        
    Raises:
        HTTPException: 404 - 需求分析元数据不存在
        
    Example:
        ```json
        {
            "id": "intent-123",
            "task_id": "550e8400-e29b-41d4-a716-446655440000",
            "roadmap_id": "python-guide-xxx",
            "parsed_goal": "Learn Python web development with Django",
            "key_technologies": ["Python", "Django", "PostgreSQL", "REST API"],
            "difficulty_profile": "intermediate",
            "time_constraint": "3 months",
            "recommended_focus": ["Backend development", "Database design"],
            "user_profile_summary": "Mid-level developer with JavaScript background",
            "skill_gap_analysis": ["Python fundamentals", "Django ORM"],
            "personalized_suggestions": ["Focus on Django best practices"],
            "estimated_learning_path_type": "backend_web",
            "content_format_weights": {
                "tutorial": 0.4,
                "resources": 0.3,
                "quiz": 0.3
            },
            "language_preferences": {
                "primary": "zh",
                "secondary": "en"
            },
            "created_at": "2024-01-01T00:00:00Z"
        }
        ```
    """
    repo = RoadmapRepository(db)
    metadata = await repo.get_intent_analysis_metadata(task_id)
    
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
