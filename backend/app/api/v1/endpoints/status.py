"""
路线图状态查询 API 端点

提供路线图运行时状态的查询功能，用于前端轮询和状态监控。

重构说明：
- ✅ 使用CurrentSession（只读操作）
- ✅ 使用自定义异常替代HTTPException
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends

from app.api.v1.deps import CurrentSession
from app.services.status_service import StatusService, get_status_service
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])

# 依赖注入
CurrentStatusService = Annotated[StatusService, Depends(get_status_service)]


@router.get("/{roadmap_id}/active-task", response_model=ResponseSchemaModel[Dict[str, Any]])
async def get_active_task(
    roadmap_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
    service: CurrentStatusService = None,
) -> ResponseSchemaModel[Dict[str, Any]]:
    """
    获取路线图当前的活跃任务
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        service: 状态服务
        
    Returns:
        活跃任务信息
    """
    result = await service.get_active_task(db, roadmap_id)
    return response_base.success(data=result)


@router.get("/{roadmap_id}/active-retry-task", response_model=ResponseSchemaModel[Dict[str, Any]])
async def get_active_retry_task(
    roadmap_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
    service: CurrentStatusService = None,
) -> ResponseSchemaModel[Dict[str, Any]]:
    """
    获取路线图当前正在进行的重试任务
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        service: 状态服务
        
    Returns:
        重试任务信息
        
    Raises:
        NotFoundError: 路线图不存在
    """
    result = await service.get_active_retry_task(db, roadmap_id)
    
    if result is None:
        raise errors.NotFoundError(msg="路线图不存在")
    
    return response_base.success(data=result)


@router.get("/{roadmap_id}/status-check", response_model=ResponseSchemaModel[Dict[str, Any]])
async def check_status_quick(
    roadmap_id: str,
    db: CurrentSession,  # ✅ 只读操作使用CurrentSession
    service: CurrentStatusService = None,
) -> ResponseSchemaModel[Dict[str, Any]]:
    """
    快速检查路线图状态，用于检测僵尸状态
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        service: 状态服务
        
    Returns:
        包含活跃任务和僵尸概念信息的字典
        
    Raises:
        NotFoundError: 路线图不存在
    """
    result = await service.check_status_quick(db, roadmap_id)
    
    if result is None:
        raise errors.NotFoundError(msg="路线图不存在")
    
    return response_base.success(data=result)
