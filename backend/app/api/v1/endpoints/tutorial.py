"""
教程管理相关端点
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository

router = APIRouter(prefix="/roadmaps", tags=["tutorial"])
logger = structlog.get_logger()


@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials")
async def get_tutorial_versions(
    roadmap_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的所有教程版本历史
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        db: 数据库会话
        
    Returns:
        教程版本列表（按版本号降序，最新版本在前）
        
    Raises:
        HTTPException: 404 - 概念没有教程
        
    Example:
        ```json
        {
            "roadmap_id": "python-web-dev-2024",
            "concept_id": "flask-basics",
            "total_versions": 3,
            "tutorials": [
                {
                    "tutorial_id": "tut-001",
                    "title": "Flask基础入门",
                    "content_version": 3,
                    "is_latest": true,
                    "content_status": "completed"
                },
                ...
            ]
        }
        ```
    """
    repo = RoadmapRepository(db)
    
    tutorials = await repo.get_tutorial_history(roadmap_id, concept_id)
    
    if not tutorials:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有教程"
        )
    
    return {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "total_versions": len(tutorials),
        "tutorials": [
            {
                "tutorial_id": t.tutorial_id,
                "title": t.title,
                "summary": t.summary,
                "content_url": t.content_url,
                "content_version": t.content_version,
                "is_latest": t.is_latest,
                "content_status": t.content_status,
                "generated_at": t.generated_at.isoformat() if t.generated_at else None,
            }
            for t in tutorials
        ]
    }


@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials/latest")
async def get_latest_tutorial(
    roadmap_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的最新教程版本
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        db: 数据库会话
        
    Returns:
        最新版本的教程元数据
        
    Raises:
        HTTPException: 404 - 概念没有教程
        
    Example:
        ```json
        {
            "roadmap_id": "python-web-dev-2024",
            "concept_id": "flask-basics",
            "tutorial_id": "tut-001",
            "title": "Flask基础入门",
            "summary": "学习Flask框架的基础知识",
            "content_url": "s3://...",
            "content_version": 3,
            "is_latest": true,
            "content_status": "completed",
            "estimated_completion_time": 2.5,
            "generated_at": "2024-01-01T00:00:00Z"
        }
        ```
    """
    repo = RoadmapRepository(db)
    
    tutorial = await repo.get_latest_tutorial(roadmap_id, concept_id)
    
    if not tutorial:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有教程"
        )
    
    return {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "tutorial_id": tutorial.tutorial_id,
        "title": tutorial.title,
        "summary": tutorial.summary,
        "content_url": tutorial.content_url,
        "content_version": tutorial.content_version,
        "is_latest": tutorial.is_latest,
        "content_status": tutorial.content_status,
        "estimated_completion_time": tutorial.estimated_completion_time,
        "generated_at": tutorial.generated_at.isoformat() if tutorial.generated_at else None,
    }


@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials/v{version}")
async def get_tutorial_by_version(
    roadmap_id: str,
    concept_id: str,
    version: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取指定概念的特定版本教程
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        version: 版本号
        db: 数据库会话
        
    Returns:
        指定版本的教程元数据
        
    Raises:
        HTTPException: 404 - 指定版本的教程不存在
        
    Example:
        ```json
        {
            "roadmap_id": "python-web-dev-2024",
            "concept_id": "flask-basics",
            "tutorial_id": "tut-001",
            "title": "Flask基础入门",
            "content_version": 2,
            "is_latest": false,
            "content_status": "completed",
            "generated_at": "2023-12-01T00:00:00Z"
        }
        ```
    """
    repo = RoadmapRepository(db)
    
    tutorial = await repo.get_tutorial_by_version(roadmap_id, concept_id, version)
    
    if not tutorial:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 的版本 v{version} 教程不存在"
        )
    
    return {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "tutorial_id": tutorial.tutorial_id,
        "title": tutorial.title,
        "summary": tutorial.summary,
        "content_url": tutorial.content_url,
        "content_version": tutorial.content_version,
        "is_latest": tutorial.is_latest,
        "content_status": tutorial.content_status,
        "estimated_completion_time": tutorial.estimated_completion_time,
        "generated_at": tutorial.generated_at.isoformat() if tutorial.generated_at else None,
    }
