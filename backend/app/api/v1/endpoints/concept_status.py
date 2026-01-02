"""
Concept 状态 API 端点

提供 Concept 内容生成状态查询接口，用于前端页面刷新后恢复状态显示。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import structlog

from app.db.session import get_db
from app.db.repositories.concept_meta_repo import ConceptMetadataRepository
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter(prefix="/concept-status", tags=["Concept Status"])


# ============================================================
# Response Models
# ============================================================

class ConceptStatusResponse(BaseModel):
    """单个 Concept 状态响应"""
    concept_id: str
    overall_status: str
    tutorial_status: str
    resources_status: str
    quiz_status: str
    tutorial_id: str | None = None
    resources_id: str | None = None
    quiz_id: str | None = None
    all_content_completed_at: str | None = None


class RoadmapConceptsStatusResponse(BaseModel):
    """Roadmap 所有 Concept 状态响应"""
    roadmap_id: str
    total_concepts: int
    completed_count: int
    concepts: List[ConceptStatusResponse]


# ============================================================
# API 端点
# ============================================================

@router.get(
    "/roadmaps/{roadmap_id}",
    response_model=RoadmapConceptsStatusResponse,
    summary="获取 Roadmap 的所有 Concept 状态",
    description="""
    获取某 roadmap 的所有 Concept 内容生成状态。
    
    **用途**：
    - 页面刷新后恢复状态显示
    - 查询内容生成进度
    
    **状态说明**：
    - `pending`: 未开始
    - `generating`: 生成中
    - `completed`: 已完成
    - `partial_failed`: 部分失败（至少一项成功）
    - `failed`: 全部失败
    """
)
async def get_roadmap_concepts_status(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取某 roadmap 的所有 Concept 内容生成状态
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        
    Returns:
        RoadmapConceptsStatusResponse: 包含所有 Concept 的状态信息
        
    Raises:
        HTTPException: 如果 roadmap 不存在
    """
    repo = ConceptMetadataRepository(db)
    concepts = await repo.get_by_roadmap_id(roadmap_id)
    
    if not concepts:
        # 可能是刚创建的 roadmap，尚未初始化 ConceptMetadata
        logger.warning(
            "roadmap_concepts_not_found",
            roadmap_id=roadmap_id,
            message="No ConceptMetadata found for this roadmap (possibly just created)"
        )
        return RoadmapConceptsStatusResponse(
            roadmap_id=roadmap_id,
            total_concepts=0,
            completed_count=0,
            concepts=[]
        )
    
    # 统计完成数量
    completed_count = sum(
        1 for c in concepts if c.overall_status == "completed"
    )
    
    # 构建响应
    concept_responses = [
        ConceptStatusResponse(
            concept_id=c.concept_id,
            overall_status=c.overall_status,
            tutorial_status=c.tutorial_status,
            resources_status=c.resources_status,
            quiz_status=c.quiz_status,
            tutorial_id=c.tutorial_id,
            resources_id=c.resources_id,
            quiz_id=c.quiz_id,
            all_content_completed_at=c.all_content_completed_at.isoformat() if c.all_content_completed_at else None,
        )
        for c in concepts
    ]
    
    logger.info(
        "roadmap_concepts_status_retrieved",
        roadmap_id=roadmap_id,
        total_concepts=len(concepts),
        completed_count=completed_count,
    )
    
    return RoadmapConceptsStatusResponse(
        roadmap_id=roadmap_id,
        total_concepts=len(concepts),
        completed_count=completed_count,
        concepts=concept_responses,
    )


@router.get(
    "/concepts/{concept_id}",
    response_model=ConceptStatusResponse,
    summary="获取单个 Concept 状态",
    description="获取指定 Concept 的内容生成状态"
)
async def get_concept_status(
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取单个 Concept 的内容生成状态
    
    Args:
        concept_id: 概念 ID
        db: 数据库会话
        
    Returns:
        ConceptStatusResponse: Concept 状态信息
        
    Raises:
        HTTPException: 如果 concept 不存在
    """
    repo = ConceptMetadataRepository(db)
    concept = await repo.get_by_concept_id(concept_id)
    
    if not concept:
        raise HTTPException(
            status_code=404,
            detail=f"Concept '{concept_id}' not found"
        )
    
    return ConceptStatusResponse(
        concept_id=concept.concept_id,
        overall_status=concept.overall_status,
        tutorial_status=concept.tutorial_status,
        resources_status=concept.resources_status,
        quiz_status=concept.quiz_status,
        tutorial_id=concept.tutorial_id,
        resources_id=concept.resources_id,
        quiz_id=concept.quiz_id,
        all_content_completed_at=concept.all_content_completed_at.isoformat() if concept.all_content_completed_at else None,
    )

