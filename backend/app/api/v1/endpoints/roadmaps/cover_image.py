"""
封面图相关 API 端点

⚠️ 架构变更（v2.0）：
- 移除 BackgroundTasks（避免 Session 泄漏）
- 改用 Celery 异步任务（独立进程，独立 Session）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import structlog

from app.db.session import get_db_transaction
from app.core.auth.deps import current_active_user
from app.models.database import User
from app.services.roadmaps.cover_image_service import CoverImageService
from app.tasks.cover_image_tasks import generate_cover_image_task, batch_generate_cover_images_task
from app.core.response_schema import response_base
from app.schemas.cover_image import (
    CoverImageResponse,
    GenerateCoverImageRequest,
    BatchGenerateRequest,
    BatchGetCoverImagesRequest,
    BatchCoverImageResponse,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/roadmaps", tags=["cover-image"])


# ============================================================
# API Endpoints
# ============================================================

@router.get("/{roadmap_id}/cover-image", response_model=CoverImageResponse)
async def get_roadmap_cover_image(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db_transaction)
):
    """
    获取路线图封面图信息（公开接口，无需认证）
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
    
    Returns:
        封面图信息
    """
    service = CoverImageService(db)
    status_info = await service.get_cover_image_status(roadmap_id)
    
    return CoverImageResponse(
        roadmap_id=roadmap_id,
        cover_image_url=status_info.url,
        status=status_info.status,
        error=status_info.error,
        retry_count=status_info.retry_count
    )


@router.post("/{roadmap_id}/cover-image/generate", response_model=CoverImageResponse)
async def generate_roadmap_cover_image(
    roadmap_id: str,
    prompt: Optional[str] = None,
    db: AsyncSession = Depends(get_db_transaction),
    current_user: User = Depends(current_active_user)
):
    """
    触发路线图封面图生成（异步 Celery 任务）
    
    ✅ 架构变更：
    - 移除 BackgroundTasks（避免 Session 泄漏）
    - 改用 Celery 异步任务（独立进程）
    
    Args:
        roadmap_id: 路线图ID
        prompt: 可选的图片生成提示词
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        封面图生成状态
    """
    service = CoverImageService(db)
    
    # 验证路线图存在
    status_info = await service.get_cover_image_status(roadmap_id)
    
    # ✅ 分发 Celery 任务（独立进程，独立 Session）
    celery_task = generate_cover_image_task.delay(
        roadmap_id=roadmap_id,
        prompt=prompt or "Generate a modern learning roadmap cover",
    )
    
    logger.info(
        "cover_image_task_dispatched",
        roadmap_id=roadmap_id,
        celery_task_id=celery_task.id,
    )
    
    return CoverImageResponse(
        roadmap_id=roadmap_id,
        cover_image_url=None,
        status="pending",
        error=None
    )


@router.post("/cover-images/batch-generate")
async def batch_generate_cover_images(
    request: BatchGenerateRequest,
    db: AsyncSession = Depends(get_db_transaction),
    current_user: User = Depends(current_active_user)
):
    """
    批量生成封面图（异步 Celery 任务）
    
    仅触发 pending/failed 状态的封面图生成，跳过已成功生成的。
    
    ✅ 架构变更：
    - 移除 BackgroundTasks（避免 Session 泄漏）
    - 改用 Celery 批量任务
    
    Args:
        request: 包含路线图ID列表的请求
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        批量生成状态，包含触发数量和跳过数量
    """
    service = CoverImageService(db)
    
    # 获取当前封面图状态
    status_map = await service.batch_get_cover_images(request.roadmap_ids)
    
    triggered_ids = []
    skipped = []
    
    # 只为 pending/failed 状态的路线图触发生成
    for roadmap_id in request.roadmap_ids:
        status_info = status_map.get(roadmap_id, {"status": "not_started"})
        status = status_info["status"]
        
        # 跳过已成功生成的
        if status == "success":
            skipped.append(roadmap_id)
            continue
        
        # 收集需要生成的路线图ID
        triggered_ids.append(roadmap_id)
    
    # ✅ 分发批量 Celery 任务
    if triggered_ids:
        celery_task = batch_generate_cover_images_task.delay(triggered_ids)
        
        logger.info(
            "batch_cover_image_task_dispatched",
            celery_task_id=celery_task.id,
            triggered_count=len(triggered_ids),
            skipped_count=len(skipped),
        )
    
    return response_base.success(data={
        "triggered": len(triggered_ids),
        "skipped": len(skipped),
        "roadmap_ids": triggered_ids,
        "message": f"Triggered {len(triggered_ids)} cover image generation tasks, skipped {len(skipped)} already successful"
    })


@router.post("/cover-images/batch-get", response_model=list[BatchCoverImageResponse])
async def batch_get_cover_images(
    request: BatchGetCoverImagesRequest,
    db: AsyncSession = Depends(get_db_transaction)
):
    """
    批量获取路线图封面图信息（公开接口，无需认证）
    
    Args:
        request: 包含路线图ID列表的请求
        db: 数据库会话
    
    Returns:
        封面图信息列表
    """
    service = CoverImageService(db)
    results = await service.batch_get_cover_images(request.roadmap_ids)
    
    return [
        BatchCoverImageResponse(
            roadmap_id=roadmap_id,
            cover_image_url=status_info.url,
            status=status_info.status,
            error=status_info.error,
            retry_count=status_info.retry_count
        )
        for roadmap_id, status_info in results.items()
    ]

