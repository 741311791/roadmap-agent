"""
资源管理相关端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository

router = APIRouter(prefix="/roadmaps", tags=["resource"])
logger = structlog.get_logger()


@router.get("/{roadmap_id}/concepts/{concept_id}/resources")
async def get_concept_resources(
    roadmap_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的学习资源
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        db: 数据库会话
        
    Returns:
        资源推荐列表
        
    Raises:
        HTTPException: 404 - 概念没有资源推荐
        
    Example:
        ```json
        {
            "roadmap_id": "python-web-dev-2024",
            "concept_id": "flask-basics",
            "resources_id": "res-001",
            "resources": [
                {
                    "title": "Flask官方文档",
                    "url": "https://flask.palletsprojects.com/",
                    "type": "official_docs",
                    "description": "Flask框架的官方文档"
                },
                {
                    "title": "Flask教程视频",
                    "url": "https://youtube.com/...",
                    "type": "video",
                    "description": "B站Flask入门视频教程"
                }
            ],
            "resources_count": 2,
            "search_queries_used": ["Flask教程", "Flask文档"],
            "generated_at": "2024-01-01T00:00:00Z"
        }
        ```
    """
    repo = RoadmapRepository(db)
    
    resources = await repo.get_resources_by_concept(concept_id, roadmap_id)
    
    if not resources:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有资源推荐"
        )
    
    return {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "resources_id": resources.id,
        "resources": resources.resources,
        "resources_count": resources.resources_count,
        "search_queries_used": resources.search_queries_used,
        "generated_at": resources.generated_at.isoformat() if resources.generated_at else None,
    }
