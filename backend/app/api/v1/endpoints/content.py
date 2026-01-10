"""
内容相关API（教程、资源、测验）

统一管理概念相关的学习内容获取。

重构说明：
- ✅ Schema定义移到独立文件（app/schemas/content.py）
- ✅ 使用CurrentSession/CurrentSessionTransaction
- ✅ 使用自定义异常替代HTTPException
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from typing import Annotated
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.v1.deps import get_current_session, CurrentContentService, CurrentSessionTransaction
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.content import (
    TutorialVersionListResponse,
    TutorialDetailResponse,
    ResourcesResponse,
    QuizResponse,
    TutorialItemResponse,
)
from app.schemas.generation import RetryContentRequest, RetryContentResponse
from app.models.database import User
from app.core.auth.deps import current_active_user

router = APIRouter(prefix="/roadmaps", tags=["content"])
logger = structlog.get_logger()


# ===== 教程相关 =====

@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials", response_model=ResponseSchemaModel[TutorialVersionListResponse])
async def get_tutorial_versions(
    roadmap_id: str,
    concept_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentContentService = None,
) -> ResponseSchemaModel[TutorialVersionListResponse]:
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
        NotFoundError: 概念没有教程
    """
    tutorials = await service.get_tutorial_versions(session, roadmap_id, concept_id)
    
    if not tutorials:
        raise errors.NotFoundError(msg=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有教程")
    
    return response_base.success(data=TutorialVersionListResponse(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        total_versions=len(tutorials),
        tutorials=[
            TutorialItemResponse(
                tutorial_id=t.tutorial_id,
                title=t.title,
                summary=t.summary,
                content_url=t.content_url,
                content_version=t.content_version,
                is_latest=t.is_latest,
                content_status=t.content_status,
                generated_at=t.generated_at.isoformat() if t.generated_at else None,
            )
            for t in tutorials
        ]
    ))


@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials/latest", response_model=ResponseSchemaModel[TutorialDetailResponse])
async def get_latest_tutorial(
    roadmap_id: str,
    concept_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentContentService = None,
) -> ResponseSchemaModel[TutorialDetailResponse]:
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
        NotFoundError: 概念没有教程
    """
    tutorial = await service.get_latest_tutorial(session, roadmap_id, concept_id)
    
    if not tutorial:
        raise errors.NotFoundError(msg=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有教程")
    
    return response_base.success(data=TutorialDetailResponse(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        tutorial_id=tutorial.tutorial_id,
        title=tutorial.title,
        summary=tutorial.summary,
        content_url=tutorial.content_url,
        content_version=tutorial.content_version,
        is_latest=tutorial.is_latest,
        content_status=tutorial.content_status,
        estimated_completion_time=tutorial.estimated_completion_time,
        generated_at=tutorial.generated_at.isoformat() if tutorial.generated_at else None,
    ))


@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials/v{version}", response_model=ResponseSchemaModel[TutorialDetailResponse])
async def get_tutorial_by_version(
    roadmap_id: str,
    concept_id: str,
    version: int,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentContentService = None,
) -> ResponseSchemaModel[TutorialDetailResponse]:
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
        NotFoundError: 指定版本的教程不存在
    """
    tutorial = await service.get_tutorial_by_version(session, roadmap_id, concept_id, version)
    
    if not tutorial:
        raise errors.NotFoundError(msg=f"概念 {concept_id} 的版本 v{version} 教程不存在")
    
    return response_base.success(data=TutorialDetailResponse(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        tutorial_id=tutorial.tutorial_id,
        title=tutorial.title,
        summary=tutorial.summary,
        content_url=tutorial.content_url,
        content_version=tutorial.content_version,
        is_latest=tutorial.is_latest,
        content_status=tutorial.content_status,
        estimated_completion_time=tutorial.estimated_completion_time,
        generated_at=tutorial.generated_at.isoformat() if tutorial.generated_at else None,
    ))


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
        教程的 Markdown 文本内容（PlainText格式）
        
    Raises:
        NotFoundError: 教程不存在或未完成
        InternalServerError: 下载失败
    """
    # 获取最新教程元数据
    tutorial = await service.get_latest_tutorial(session, roadmap_id, concept_id)
    
    if not tutorial:
        raise errors.NotFoundError(msg=f"Concept {concept_id} in roadmap {roadmap_id} has no tutorial")
    
    if tutorial.content_status != "completed":
        raise errors.NotFoundError(msg=f"Tutorial is not ready yet (status: {tutorial.content_status})")
    
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
        
        if "not found" in error_msg.lower() or "nosuchkey" in error_msg.lower():
            logger.warning(
                "tutorial_content_not_found",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                error=error_msg,
            )
            raise errors.NotFoundError(msg=error_msg)
        
        logger.error(
            "tutorial_content_download_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            error=error_msg,
        )
        raise errors.InternalServerError(msg=f"下载教程内容失败: {error_msg}")


# ===== 资源推荐相关 =====

@router.get("/{roadmap_id}/concepts/{concept_id}/resources", response_model=ResponseSchemaModel[ResourcesResponse])
async def get_concept_resources(
    roadmap_id: str,
    concept_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentContentService = None,
) -> ResponseSchemaModel[ResourcesResponse]:
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
        NotFoundError: 概念没有资源推荐
    """
    resources = await service.get_concept_resources(session, roadmap_id, concept_id)
    
    if not resources:
        raise errors.NotFoundError(msg=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有资源推荐")
    
    return response_base.success(data=ResourcesResponse(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        resources_id=resources.id,
        resources=resources.resources,
        resources_count=resources.resources_count,
        search_queries_used=resources.search_queries_used,
        generated_at=resources.generated_at.isoformat() if resources.generated_at else None,
    ))


# ===== 测验相关 =====

@router.get("/{roadmap_id}/concepts/{concept_id}/quiz", response_model=ResponseSchemaModel[QuizResponse])
async def get_concept_quiz(
    roadmap_id: str,
    concept_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentContentService = None,
) -> ResponseSchemaModel[QuizResponse]:
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
        NotFoundError: 概念没有测验
    """
    quiz = await service.get_concept_quiz(session, roadmap_id, concept_id)
    
    if not quiz:
        raise errors.NotFoundError(msg=f"概念 {concept_id} 在路线图 {roadmap_id} 中没有测验")
    
    return response_base.success(data=QuizResponse(
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        quiz_id=quiz.quiz_id,
        questions=quiz.questions,
        total_questions=quiz.total_questions,
        easy_count=quiz.easy_count,
        medium_count=quiz.medium_count,
        hard_count=quiz.hard_count,
        generated_at=quiz.generated_at.isoformat() if quiz.generated_at else None,
    ))


# ============================================================
# 单个概念内容重试 API（已废弃 - LangGraph 1.0 迁移）
# 
# 注意：这些端点已废弃，不再使用。
# 原因：LangGraph 子图模式 + Checkpointer 自动处理重试。
# 保留这些端点仅为了向后兼容，返回 501 Not Implemented。
# ============================================================


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/tutorial/retry",
    response_model=ResponseSchemaModel[RetryContentResponse],
    deprecated=True,
)
async def retry_tutorial_deprecated(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    content_service: CurrentContentService,
    session: CurrentSessionTransaction,
    current_user: User = Depends(current_active_user),
) -> ResponseSchemaModel[RetryContentResponse]:
    """
    ⚠️ 已废弃：重试单个概念的教程生成
    
    废弃原因：
    - LangGraph 1.0 迁移后，使用子图模式 + Checkpointer 自动处理重试
    - 不再需要手动重试端点
    
    替代方案：
    - LangGraph Node RetryPolicy 自动重试（5 次）
    - Checkpointer 断点续传（用户可重新生成整个路线图）
    """
    from fastapi import HTTPException
    raise HTTPException(
        status_code=501,
        detail="This endpoint is deprecated. Content retry is now handled automatically by LangGraph Checkpointer. Please regenerate the entire roadmap if needed."
    )


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/resources/retry",
    response_model=ResponseSchemaModel[RetryContentResponse],
    deprecated=True,
)
async def retry_resources_deprecated(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    content_service: CurrentContentService,
    session: CurrentSessionTransaction,  # ✅ 写操作使用CurrentSessionTransaction
    current_user: User = Depends(current_active_user),
) -> ResponseSchemaModel[RetryContentResponse]:
    """
    ⚠️ 已废弃：重试单个概念的资源推荐生成
    
    废弃原因：LangGraph 1.0 迁移，使用 Checkpointer 自动处理重试
    """
    from fastapi import HTTPException
    raise HTTPException(
        status_code=501,
        detail="This endpoint is deprecated. Content retry is now handled automatically by LangGraph Checkpointer."
    )


@router.post(
    "/{roadmap_id}/concepts/{concept_id}/quiz/retry",
    response_model=ResponseSchemaModel[RetryContentResponse],
    deprecated=True,
)
async def retry_quiz_deprecated(
    roadmap_id: str,
    concept_id: str,
    request: RetryContentRequest,
    content_service: CurrentContentService,
    session: CurrentSessionTransaction,  # ✅ 写操作使用CurrentSessionTransaction
    current_user: User = Depends(current_active_user),
) -> ResponseSchemaModel[RetryContentResponse]:
    """
    ⚠️ 已废弃：重试单个概念的测验生成
    
    废弃原因：LangGraph 1.0 迁移，使用 Checkpointer 自动处理重试
    """
    from fastapi import HTTPException
    raise HTTPException(
        status_code=501,
        detail="This endpoint is deprecated. Content retry is now handled automatically by LangGraph Checkpointer."
    )
