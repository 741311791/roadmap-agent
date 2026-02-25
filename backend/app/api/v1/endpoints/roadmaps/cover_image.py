"""
封面图相关 API 端点

⚠️ 架构变更（v2.0）：
- 移除 BackgroundTasks（避免 Session 泄漏）
- 改用 Celery 异步任务（独立进程，独立 Session）
"""
import asyncio
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import structlog

from app.db.session import get_db_transaction
from app.core.auth.deps import current_active_user
from app.models.database import User, RoadmapTask, beijing_now
from app.services.roadmaps.cover_image_service import CoverImageService
from app.tasks.cover_image_tasks import generate_cover_image_task
from app.crud.crud_roadmap import get_roadmap_crud
from app.core.response_schema import response_base
from app.schemas.cover_image import (
    CoverImageResponse,
    GenerateCoverImageRequest,
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
    - 在 roadmap_tasks 表创建 task 记录以追踪任务状态
    
    Args:
        roadmap_id: 路线图ID
        prompt: 可选的图片生成提示词
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        封面图生成状态（含 task_id）
    """
    service = CoverImageService(db)
    
    # 验证路线图封面图状态
    await service.get_cover_image_status(roadmap_id)
    
    # 查询路线图标题，作为图片生成的默认 prompt
    roadmap_crud = get_roadmap_crud()
    roadmap_meta = await roadmap_crud.get_by_roadmap_id(db, roadmap_id)
    if roadmap_meta is None:
        raise HTTPException(status_code=404, detail=f"Roadmap {roadmap_id} not found")
    
    effective_prompt = prompt or roadmap_meta.title
    
    # 在 roadmap_tasks 表创建任务记录，用于追踪封面图生成进度
    task_id = str(uuid.uuid4())
    new_task = RoadmapTask(
        task_id=task_id,
        user_id=str(current_user.id),
        status="pending",
        current_step="queued",
        user_request={"roadmap_id": roadmap_id, "prompt": effective_prompt},
        roadmap_id=roadmap_id,
        task_type="cover_image",
    )
    db.add(new_task)
    await db.flush()
    
    # ✅ 分发 Celery 任务（独立进程，独立 Session），传入 task_id 以更新任务状态
    # 使用 asyncio.to_thread 避免 .delay() 同步阻塞事件循环
    celery_task = await asyncio.to_thread(
        generate_cover_image_task.apply_async,
        kwargs={
            "roadmap_id": roadmap_id,
            "prompt": effective_prompt,
            "task_id": task_id,
        },
    )
    
    # 记录 Celery 任务 ID
    new_task.celery_task_id = celery_task.id
    await db.flush()
    
    logger.info(
        "cover_image_task_dispatched",
        roadmap_id=roadmap_id,
        celery_task_id=celery_task.id,
        task_id=task_id,
    )
    
    return CoverImageResponse(
        roadmap_id=roadmap_id,
        cover_image_url=None,
        status="pending",
        error=None,
        task_id=task_id,
    )


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

