"""
教程管理相关端点
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import unquote
import structlog

from app.db.session import get_db
from app.db.repositories.roadmap_repo import RoadmapRepository
from app.core.tool_registry import tool_registry
from app.models.domain import S3DownloadRequest

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


@router.get("/{roadmap_id}/concepts/{concept_id}/tutorials/latest/content", response_class=PlainTextResponse)
async def download_latest_tutorial_content(
    roadmap_id: str,
    concept_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    下载最新版本教程的 Markdown 内容（后端代理）
    
    此端点解决 CORS 问题：
    - 前端不直接访问 R2/S3 URL（会有 CORS 限制）
    - 通过后端代理下载内容
    - 返回纯文本 Markdown
    
    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        db: 数据库会话
        
    Returns:
        教程的 Markdown 文本内容
        
    Raises:
        HTTPException: 404 - 教程不存在或未完成
        HTTPException: 500 - 下载失败
        
    Example:
        ```
        GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest/content
        
        Response (text/plain):
        # Introduction to Python
        
        Python is a high-level programming language...
        ```
    """
    repo = RoadmapRepository(db)
    
    # 1. 获取最新教程元数据
    tutorial = await repo.get_latest_tutorial(roadmap_id, concept_id)
    
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
    
    # 2. 从 content_url 提取 S3 key 和 bucket
    content_url = tutorial.content_url
    s3_key = content_url
    s3_bucket = None  # 从 URL 中提取，或使用默认值
    
    # 如果是完整 URL，提取 bucket 和 key
    if "://" in content_url:
        # URL 格式可能是：
        # - R2: https://xxx.r2.cloudflarestorage.com/roadmap-content/key...
        # - MinIO: http://47.111.115.130:9000/roadmap/key...
        
        parts = content_url.split("/")
        
        # 尝试识别 bucket（通常在 host 后的第一个部分）
        # MinIO: protocol://host:port/bucket/key...
        # R2: protocol://host/bucket/key...
        
        if len(parts) >= 4:
            # 假设 parts[3] 是 bucket
            potential_bucket = parts[3]
            
            # 检查这是否是合法的 bucket 名称
            # bucket 名称通常不包含 % 编码，且不是 key 的一部分
            if "%" not in potential_bucket and ":" not in potential_bucket:
                s3_bucket = potential_bucket
                # key 从 bucket 后开始
                s3_key = "/".join(parts[4:])
            else:
                # 如果无法识别 bucket，使用默认值
                from app.config.settings import settings
                s3_bucket = settings.S3_BUCKET_NAME
                s3_key = "/".join(parts[4:])
    
    # 如果没有从 URL 提取到 bucket，使用默认值
    if not s3_bucket:
        from app.config.settings import settings
        s3_bucket = settings.S3_BUCKET_NAME
    
    # 移除 URL 参数（预签名参数）
    if "?" in s3_key:
        s3_key = s3_key.split("?")[0]
    
    # 解码 URL 编码的字符（如 %3A -> :）
    s3_key = unquote(s3_key)
    
    logger.info(
        "tutorial_content_download_requested",
        roadmap_id=roadmap_id,
        concept_id=concept_id,
        tutorial_id=tutorial.tutorial_id,
        original_url=content_url,
        extracted_bucket=s3_bucket,
        extracted_key=s3_key,
    )
    
    # 3. 从 S3 下载内容
    try:
        s3_tool = tool_registry.get("s3_storage_v1")
        if not s3_tool:
            raise HTTPException(
                status_code=500,
                detail="S3 Storage Tool not available"
            )
        
        download_request = S3DownloadRequest(key=s3_key, bucket=s3_bucket)
        download_result = await s3_tool.download(download_request)
        
        if not download_result.success or not download_result.content:
            raise HTTPException(
                status_code=500,
                detail="Failed to download tutorial content from storage"
            )
        
        logger.info(
            "tutorial_content_downloaded",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            bucket=s3_bucket,
            key=s3_key,
            content_length=len(download_result.content),
        )
        
        return download_result.content
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        
        # 如果是 NoSuchKey 错误，返回 404 而不是 500
        if "NoSuchKey" in error_msg or "does not exist" in error_msg:
            logger.warning(
                "tutorial_content_not_found",
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                bucket=s3_bucket,
                key=s3_key,
                error=error_msg,
            )
            raise HTTPException(
                status_code=404,
                detail=f"Tutorial content not found in storage (key: {s3_key})"
            )
        
        # 其他错误返回 500
        logger.error(
            "tutorial_content_download_failed",
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            bucket=s3_bucket,
            key=s3_key,
            error=error_msg,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to download tutorial content: {error_msg}"
        )
