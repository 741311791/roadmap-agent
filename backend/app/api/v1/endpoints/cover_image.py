"""
封面图相关 API 端点
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from pydantic import BaseModel

from app.db.session import get_db
from app.core.auth.deps import current_active_user
from app.models.database import User
from app.services.cover_image_service import CoverImageService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================
# Response Models
# ============================================================

class CoverImageResponse(BaseModel):
    """封面图响应模型"""
    roadmap_id: str
    cover_image_url: Optional[str] = None
    status: str  # not_started, pending, generating, success, failed
    error: Optional[str] = None
    retry_count: Optional[int] = None


class GenerateCoverImageRequest(BaseModel):
    """生成封面图请求模型"""
    roadmap_id: str
    prompt: Optional[str] = None


# ============================================================
# API Endpoints
# ============================================================

@router.get("/roadmap/{roadmap_id}/cover-image", response_model=CoverImageResponse)
async def get_roadmap_cover_image(
    roadmap_id: str,
    db: AsyncSession = Depends(get_db)
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
        cover_image_url=status_info["url"],
        status=status_info["status"],
        error=status_info.get("error"),
        retry_count=status_info.get("retry_count")
    )


@router.post("/roadmap/{roadmap_id}/cover-image/generate", response_model=CoverImageResponse)
async def generate_roadmap_cover_image(
    roadmap_id: str,
    background_tasks: BackgroundTasks,
    prompt: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    """
    触发路线图封面图生成（异步）
    
    Args:
        roadmap_id: 路线图ID
        background_tasks: 后台任务
        prompt: 可选的图片生成提示词
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        封面图生成状态
    """
    service = CoverImageService(db)
    
    # 在后台任务中生成封面图
    background_tasks.add_task(
        service.generate_cover_image,
        roadmap_id=roadmap_id,
        prompt=prompt
    )
    
    return CoverImageResponse(
        roadmap_id=roadmap_id,
        cover_image_url=None,
        status="generating",
        error=None
    )


@router.post("/roadmap/{roadmap_id}/cover-image/generate-sync", response_model=CoverImageResponse)
async def generate_roadmap_cover_image_sync(
    roadmap_id: str,
    prompt: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    """
    同步生成路线图封面图（等待生成完成）
    
    Args:
        roadmap_id: 路线图ID
        prompt: 可选的图片生成提示词
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        封面图信息
    """
    service = CoverImageService(db)
    
    try:
        cover_image_url = await service.generate_cover_image(
            roadmap_id=roadmap_id,
            prompt=prompt
        )
        
        status_info = service.get_cover_image_status(roadmap_id)
        
        return CoverImageResponse(
            roadmap_id=roadmap_id,
            cover_image_url=cover_image_url,
            status=status_info["status"],
            error=status_info.get("error"),
            retry_count=status_info.get("retry_count")
        )
    
    except Exception as e:
        logger.exception(f"同步生成封面图失败: roadmap_id={roadmap_id}")
        raise HTTPException(
            status_code=500,
            detail=f"封面图生成失败: {str(e)}"
        )


@router.post("/cover-images/batch-generate")
async def batch_generate_cover_images(
    roadmap_ids: list[str],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    """
    批量生成封面图（异步）
    
    Args:
        roadmap_ids: 路线图ID列表
        background_tasks: 后台任务
        db: 数据库会话
        current_user: 当前用户
    
    Returns:
        批量生成状态
    """
    service = CoverImageService(db)
    
    # 为每个路线图添加后台任务
    for roadmap_id in roadmap_ids:
        background_tasks.add_task(
            service.generate_cover_image,
            roadmap_id=roadmap_id
        )
    
    return {
        "message": f"已提交 {len(roadmap_ids)} 个封面图生成任务",
        "roadmap_ids": roadmap_ids
    }

