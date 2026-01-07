"""
内容相关API（教程、资源、测验）

统一管理概念相关的学习内容获取
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.v1.deps import get_current_session, CurrentContentService

router = APIRouter(prefix="/roadmaps", tags=["content"])
logger = structlog.get_logger()


# ===== 教程相关 =====

@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials")
async def get_tutorial_versions(
    roadmap_id: str,
    concept_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentContentService = None,
):
    """
    获取指定概念的所有教程版本历史
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        session: 数据库会话
        service: 内容服务
        
    Returns:
        教程版本列表（按版本号降序，最新版本在前）
        
    Raises:
        HTTPException: 404 - 概念没有教程
    """
    tutorials = await service.get_tutorial_versions(session, roadmap_id, concept_id)
    
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
    session: AsyncSession = Depends(get_current_session),
    service: CurrentContentService = None,
):
    """
    获取指定概念的最新教程版本
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        session: 数据库会话
        service: 内容服务
        
    Returns:
        最新版本的教程元数据
        
    Raises:
        HTTPException: 404 - 概念没有教程
    """
    tutorial = await service.get_latest_tutorial(session, roadmap_id, concept_id)
    
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
    session: AsyncSession = Depends(get_current_session),
    service: CurrentContentService = None,
):
    """
    获取指定概念的特定版本教程
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        version: 版本号
        session: 数据库会话
        service: 内容服务
        
    Returns:
        指定版本的教程元数据
        
    Raises:
        HTTPException: 404 - 指定版本的教程不存在
    """
    tutorial = await service.get_tutorial_by_version(session, roadmap_id, concept_id, version)
    
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


@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials/latest/content", response_class=PlainTextResponse)
async def download_latest_tutorial_content(
    roadmap_id: str,
    concept_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentContentService = None,
):
    """
    下载最新版本教程的 Markdown 内容（后端代理）
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        session: 数据库会话
        service: 内容服务
        
    Returns:
        教程的 Markdown 文本内容
        
    Raises:
        HTTPException: 404 - 教程不存在或未完成
        HTTPException: 500 - 下载失败
    """
    # 获取最新教程元数据
    tutorial = await service.get_latest_tutorial(session, roadmap_id, concept_id)
    
    if not tutorial:
        raise HTTPException(
            status_code=404,
            detail=f"Concept {concept_id} in roadmap {roadmap_id} has no tutorial"
        )
    
    if tutorial.content_status != "completed":
        raise HTTPException(
            status_code=404,
            detail=f"Tutorial is not ready yet (status: {tutorial.content_status})"
        )
    
    # 下载内容（S3逻辑在Service层）
    try:
        content = await service.download_tutorial_content(tutorial)
        
        logger.info(
            "tutorial_content_downloaded",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            content_length=len(content),
        )
        
        return content
        
    except ValueError as e:
        error_msg = str(e)
        
        if "not found" in error_msg.lower() or "nosuchwkey" in error_msg.lower():
            logger.warning(
                "tutorial_content_not_found",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                error=error_msg,
            )
            raise HTTPException(status_code=404, detail=error_msg)
        
        logger.error(
            "tutorial_content_download_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=error_msg,
        )
        raise HTTPException(status_code=500, detail=f"Failed to download tutorial content: {error_msg}")


# ===== 资源推荐相关 =====

@router.get("/{roadmap_id}/concepts/{concept_id}/resources")
async def get_concept_resources(
    roadmap_id: str,
    concept_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentContentService = None,
):
    """
    获取指定概念的学习资源
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        session: 数据库会话
        service: 内容服务
        
    Returns:
        资源推荐列表
        
    Raises:
        HTTPException: 404 - 概念没有资源推荐
    """
    resources = await service.get_concept_resources(session, roadmap_id, concept_id)
    
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


# ===== 测验相关 =====

@router.get("/{roadmap_id}/concepts/{concept_id}/quiz")
async def get_concept_quiz(
    roadmap_id: str,
    concept_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentContentService = None,
):
    """
    获取指定概念的测验
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        session: 数据库会话
        service: 内容服务
        
    Returns:
        测验数据，包含题目列表
        
    Raises:
        HTTPException: 404 - 概念没有测验
    """
    quiz = await service.get_concept_quiz(session, roadmap_id, concept_id)
    
    if not quiz:
        raise HTTPException(
            status_code=404,
            detail=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有测验"
        )
    
    return {
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "quiz_id": quiz.quiz_id,
        "questions": quiz.questions,
        "total_questions": quiz.total_questions,
        "easy_count": quiz.easy_count,
        "medium_count": quiz.medium_count,
        "hard_count": quiz.hard_count,
        "generated_at": quiz.generated_at.isoformat() if quiz.generated_at else None,
    }
