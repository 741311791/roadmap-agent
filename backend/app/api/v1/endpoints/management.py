"""
路线图管理 API 端点

提供路线图的删除、恢复、永久删除等管理功能。
"""
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.v1.deps import get_current_session
from app.services.management_service import ManagementService, get_management_service

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])
logger = structlog.get_logger()

# 依赖注入
CurrentManagementService = Annotated[ManagementService, Depends(get_management_service)]


@router.delete("/{roadmap_id}")
async def delete_roadmap(
    roadmap_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentManagementService = None,
):
    """
    删除路线图
    
    根据 roadmap_id 格式自动判断删除方式：
    1. task-前缀：物理删除任务
    2. 普通格式：软删除路线图
    
    Args:
        roadmap_id: 路线图 ID
        user_id: 用户 ID
        session: 数据库会话
        service: 管理服务
        
    Returns:
        删除结果
        
    Raises:
        HTTPException: 404/403/500
    """
    try:
        result = await service.delete_roadmap(session, roadmap_id, user_id)
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("delete_roadmap_failed", roadmap_id=roadmap_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{roadmap_id}/restore")
async def restore_roadmap(
    roadmap_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentManagementService = None,
):
    """
    从回收站恢复路线图
    
    Args:
        roadmap_id: 路线图 ID
        user_id: 用户 ID
        session: 数据库会话
        service: 管理服务
        
    Returns:
        恢复结果
    """
    try:
        result = await service.restore_roadmap(session, roadmap_id, user_id)
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("restore_roadmap_failed", roadmap_id=roadmap_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{roadmap_id}/permanent")
async def permanently_delete_roadmap(
    roadmap_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_current_session),
    service: CurrentManagementService = None,
):
    """
    永久删除路线图（不可恢复）
    
    ⚠️ 警告：此操作会永久删除所有数据
    
    Args:
        roadmap_id: 路线图 ID
        user_id: 用户 ID
        session: 数据库会话
        service: 管理服务
        
    Returns:
        删除结果
    """
    try:
        result = await service.permanently_delete_roadmap(session, roadmap_id, user_id)
        await session.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("permanently_delete_failed", roadmap_id=roadmap_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
