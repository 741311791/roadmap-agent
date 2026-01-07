"""
路线图状态查询 API 端点

提供路线图运行时状态的查询功能，用于前端轮询和状态监控。
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_session
from app.services.status_service import StatusService, get_status_service

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])

# 依赖注入
CurrentStatusService = Annotated[StatusService, Depends(get_status_service)]


@router.get("/{roadmap_id}/active-task")
async def get_active_task(
    roadmap_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentStatusService = None,
):
    """
    获取路线图当前的活跃任务
    
    Args:
        roadmap_id: 路线图 ID
        session: 数据库会话
        service: 状态服务
        
    Returns:
        活跃任务信息
    """
    return await service.get_active_task(session, roadmap_id)


@router.get("/{roadmap_id}/active-retry-task")
async def get_active_retry_task(
    roadmap_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentStatusService = None,
):
    """
    获取路线图当前正在进行的重试任务
    
    Args:
        roadmap_id: 路线图 ID
        session: 数据库会话
        service: 状态服务
        
    Returns:
        重试任务信息
        
    Raises:
        HTTPException: 404 - 路线图不存在
    """
    result = await service.get_active_retry_task(session, roadmap_id)
    
    if result is None:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    
    return result


@router.get("/{roadmap_id}/status-check")
async def check_status_quick(
    roadmap_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentStatusService = None,
):
    """
    快速检查路线图状态，用于检测僵尸状态
    
    Args:
        roadmap_id: 路线图 ID
        session: 数据库会话
        service: 状态服务
        
    Returns:
        包含活跃任务和僵尸概念信息的字典
        
    Raises:
        HTTPException: 404 - 路线图不存在
    """
    result = await service.check_status_quick(session, roadmap_id)
    
    if result is None:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    
    return result
