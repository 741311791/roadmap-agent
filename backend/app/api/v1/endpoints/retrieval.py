"""
路线图查询相关端点
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.v1.deps import get_current_session
from app.services.retrieval_service import RetrievalService, get_retrieval_service

router = APIRouter(prefix="/roadmaps", tags=["retrieval"])
logger = structlog.get_logger()

# 依赖注入
CurrentRetrievalService = Annotated[RetrievalService, Depends(get_retrieval_service)]


@router.get("/{roadmap_id}")
async def get_roadmap(
    roadmap_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentRetrievalService = None,
):
    """
    获取完整的路线图数据
    
    Args:
        roadmap_id: 路线图ID
        session: 数据库会话
        service: 检索服务
        
    Returns:
        - 如果路线图存在，返回完整的路线图框架数据
        - 如果路线图不存在但有活跃任务，返回生成中状态
        - 如果都不存在，返回 404
        
    Raises:
        HTTPException: 404 - 路线图不存在
    """
    # 调用Service层获取路线图
    roadmap = await service.get_roadmap_with_status(session, roadmap_id)
    
    if not roadmap:
        # 检查是否有活跃任务正在生成这个路线图
        active_task = await service.get_active_task_by_roadmap(session, roadmap_id)
        
        if active_task:
            # 路线图正在生成中
            return {
                "status": "processing",
                "task_id": active_task.task_id,
                "current_step": active_task.current_step,
                "message": "路线图正在生成中",
                "created_at": active_task.created_at.isoformat() if active_task.created_at else None,
                "updated_at": active_task.updated_at.isoformat() if active_task.updated_at else None,
            }
        
        # 路线图不存在且没有活跃任务
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    return roadmap
