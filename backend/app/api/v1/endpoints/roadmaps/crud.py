"""
路线图CRUD API 端点

提供路线图的获取、删除、恢复、永久删除、状态检查等核心CRUD功能。

重构变更：
- ✅ 合并多个文件的CRUD接口：
  - roadmaps/retrieval.py: 获取路线图详情
  - roadmaps/management.py: 删除、恢复、永久删除
  - roadmaps/status.py: 快速状态检查
- ✅ 统一到 /roadmaps prefix
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends
import structlog

from app.api.v1.deps import CurrentSession, CurrentSessionTransaction
from app.models.database import User
from app.core.auth.deps import current_active_user
from app.services.roadmaps.retrieval_service import RetrievalService, get_retrieval_service
from app.services.roadmaps.management_service import ManagementService, get_management_service
from app.services.roadmaps.status_service import StatusService, get_status_service
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.roadmap import (
    RoadmapDetailResponse,
    RoadmapDeleteResponse,
    RoadmapRestoreResponse,
    RoadmapPermanentDeleteResponse,
    RoadmapStatusResponse,
    RoadmapStatusQuickResponse,
    StaleConceptItem,
    ActiveTaskItem,
)

router = APIRouter(prefix="/roadmaps", tags=["roadmap-crud"])
logger = structlog.get_logger()

# 依赖注入
CurrentRetrievalService = Annotated[RetrievalService, Depends(get_retrieval_service)]
CurrentManagementService = Annotated[ManagementService, Depends(get_management_service)]
CurrentStatusService = Annotated[StatusService, Depends(get_status_service)]


@router.get("/{roadmap_id}", response_model=ResponseSchemaModel[RoadmapDetailResponse])
async def get_roadmap(
    roadmap_id: str,
    db: CurrentSession,
    service: CurrentRetrievalService = None,
) -> ResponseSchemaModel[RoadmapDetailResponse]:
    """
    获取完整的路线图数据
    
    根据路线图状态返回不同格式：
    - 已完成: 返回完整框架数据
    - 生成中: 返回任务状态（framework=None）
    - 不存在: 返回 404
    
    Args:
        roadmap_id: 路线图ID
        db: 数据库会话
        service: 检索服务
        
    Returns:
        路线图详情（包含 framework、status、任务信息等）
        
    Raises:
        NotFoundError: 路线图不存在
    """
    # 1. 尝试获取路线图
    roadmap = await service.get_roadmap_with_status(db, roadmap_id)
    
    if roadmap:
        # ✅ 路线图存在，直接返回（可能是生成中或已完成）
        return response_base.success(data=roadmap)
    
    # 2. 路线图不存在，检查是否有活跃任务正在生成
    active_task = await service.get_active_task_by_roadmap(db, roadmap_id)
    
    if active_task:
        # ✅ 有活跃任务，返回生成中状态（符合新的 Schema 定义）
        user_request = active_task.user_request or {}
        return response_base.success(data=RoadmapDetailResponse(
            roadmap_id=roadmap_id,
            user_id=active_task.user_id,
            learning_goal=user_request.get("preferences", {}).get("learning_goal", ""),
            created_at=active_task.created_at.isoformat() if active_task.created_at else "",
            updated_at=active_task.updated_at.isoformat() if active_task.updated_at else "",
            framework=None,  # ✅ 生成中时为 None
            status="processing",
            task_id=active_task.task_id,
            current_step=active_task.current_step,
            message="路线图正在生成中",
        ))
    
    # 3. 路线图不存在且没有活跃任务
    raise errors.NotFoundError(msg="路线图不存在")


@router.get("/{roadmap_id}/status", response_model=ResponseSchemaModel[RoadmapStatusResponse])
async def get_roadmap_status(
    roadmap_id: str,
    db: CurrentSession,
    service: CurrentStatusService = None,
) -> ResponseSchemaModel[RoadmapStatusResponse]:
    """
    获取路线图状态
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        service: 状态服务
        
    Returns:
        路线图状态信息（roadmap_id、status、task_id）
        
    Raises:
        NotFoundError: 路线图不存在
    """
    result = await service.get_roadmap_status(db, roadmap_id)
    
    if result is None:
        raise errors.NotFoundError(msg="路线图不存在")
    
    return response_base.success(data=RoadmapStatusResponse(**result))


@router.get("/{roadmap_id}/status/quick", response_model=ResponseSchemaModel[RoadmapStatusQuickResponse])
async def check_roadmap_status_quick(
    roadmap_id: str,
    db: CurrentSession,
    service: CurrentStatusService = None,
) -> ResponseSchemaModel[RoadmapStatusQuickResponse]:
    """
    快速检查路线图状态，用于检测僵尸状态
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话
        service: 状态服务
        
    Returns:
        包含活跃任务和僵尸概念信息的详细状态
        
    Raises:
        NotFoundError: 路线图不存在
    """
    result = await service.check_status_quick(db, roadmap_id)
    
    if result is None:
        raise errors.NotFoundError(msg="路线图不存在")
    
    stale_concepts = [
        StaleConceptItem(**item)
        for item in result.get("stale_concepts", [])
    ]
    active_tasks = [
        ActiveTaskItem(**item)
        for item in result.get("active_tasks", [])
    ]
    
    return response_base.success(data=RoadmapStatusQuickResponse(
        roadmap_id=roadmap_id,
        has_active_task=result.get("has_active_task", False),
        active_tasks=active_tasks,
        stale_concepts=stale_concepts,
        zombie_count=len(stale_concepts),
    ))


@router.delete("/{roadmap_id}", response_model=ResponseSchemaModel[RoadmapDeleteResponse])
async def delete_roadmap(
    roadmap_id: str,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_active_user),
    service: CurrentManagementService = None,
) -> ResponseSchemaModel[RoadmapDeleteResponse]:
    """
    删除路线图（软删除）
    
    根据 roadmap_id 格式自动判断删除方式：
    1. task-前缀：物理删除任务记录
    2. 普通格式：软删除路线图（移到回收站）
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话（自动commit/rollback）
        current_user: 当前用户（从JWT获取，防止伪造）
        service: 管理服务
        
    Returns:
        删除结果
        
    Raises:
        NotFoundError: 路线图不存在
        ForbiddenError: 无权限删除此路线图
        InternalServerError: 删除失败
    """
    try:
        result = await service.delete_roadmap(
            session=db,
            roadmap_id=roadmap_id,
            user_id=current_user.id
        )
        
        logger.info(
            "roadmap_deleted",
            roadmap_id=roadmap_id,
            user_id=current_user.id,
        )
        
        return response_base.success(data=result)
        
    except ValueError as e:
        raise errors.NotFoundError(msg=str(e))
    except PermissionError as e:
        raise errors.ForbiddenError(msg=str(e))
    except Exception as e:
        logger.error(
            "delete_roadmap_failed",
            roadmap_id=roadmap_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise errors.InternalServerError(msg="删除失败")


@router.post("/{roadmap_id}/restore", response_model=ResponseSchemaModel[RoadmapRestoreResponse])
async def restore_roadmap(
    roadmap_id: str,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_active_user),
    service: CurrentManagementService = None,
) -> ResponseSchemaModel[RoadmapRestoreResponse]:
    """
    从回收站恢复路线图
    
    将软删除的路线图恢复到正常状态。
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话（自动commit/rollback）
        current_user: 当前用户（从JWT获取）
        service: 管理服务
        
    Returns:
        恢复结果
        
    Raises:
        NotFoundError: 路线图不存在或未被删除
        ForbiddenError: 无权限恢复此路线图
        InternalServerError: 恢复失败
    """
    try:
        result = await service.restore_roadmap(
            session=db,
            roadmap_id=roadmap_id,
            user_id=current_user.id
        )
        
        logger.info(
            "roadmap_restored",
            roadmap_id=roadmap_id,
            user_id=current_user.id,
        )
        
        return response_base.success(data=result)
        
    except ValueError as e:
        raise errors.NotFoundError(msg=str(e))
    except PermissionError as e:
        raise errors.ForbiddenError(msg=str(e))
    except Exception as e:
        logger.error(
            "restore_roadmap_failed",
            roadmap_id=roadmap_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise errors.InternalServerError(msg="恢复失败")


@router.delete("/{roadmap_id}/permanent", response_model=ResponseSchemaModel[RoadmapPermanentDeleteResponse])
async def permanently_delete_roadmap(
    roadmap_id: str,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_active_user),
    service: CurrentManagementService = None,
) -> ResponseSchemaModel[RoadmapPermanentDeleteResponse]:
    """
    永久删除路线图（不可恢复）
    
    ⚠️ 警告：此操作会永久删除所有相关数据，包括：
    - 路线图元数据
    - 所有概念(Concept)
    - 教程(Tutorial)
    - 资源推荐(Resource)
    - 测验(Quiz)
    - 学习进度
    
    Args:
        roadmap_id: 路线图 ID
        db: 数据库会话（自动commit/rollback）
        current_user: 当前用户（从JWT获取）
        service: 管理服务
        
    Returns:
        删除结果
        
    Raises:
        NotFoundError: 路线图不存在
        ForbiddenError: 无权限删除此路线图
        InternalServerError: 删除失败
    """
    try:
        result = await service.permanently_delete_roadmap(
            session=db,
            roadmap_id=roadmap_id,
            user_id=current_user.id
        )
        
        logger.info(
            "roadmap_permanently_deleted",
            roadmap_id=roadmap_id,
            user_id=current_user.id,
        )
        
        return response_base.success(data=result)
        
    except ValueError as e:
        raise errors.NotFoundError(msg=str(e))
    except PermissionError as e:
        raise errors.ForbiddenError(msg=str(e))
    except Exception as e:
        logger.error(
            "permanently_delete_failed",
            roadmap_id=roadmap_id,
            user_id=current_user.id,
            error=str(e),
        )
        raise errors.InternalServerError(msg="永久删除失败")

