"""
路线图管理 API 端点

提供路线图的删除、恢复、永久删除等管理功能。

重构说明：
- ✅ 添加JWT身份验证（从token获取user_id，防止伪造）
- ✅ 使用CurrentSessionTransaction自动管理事务
- ✅ 使用自定义异常替代HTTPException
- ✅ 使用统一响应格式（ResponseSchemaModel）
- ✅ 符合企业级架构规范
"""
from typing import Annotated, Dict, Any
from fastapi import APIRouter, Depends
import structlog

from app.api.v1.deps import CurrentSessionTransaction
from app.models.database import User
from app.core.auth.deps import current_active_user
from app.services.management_service import ManagementService, get_management_service
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base

router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])
logger = structlog.get_logger()

# 依赖注入
CurrentManagementService = Annotated[ManagementService, Depends(get_management_service)]


@router.delete("/{roadmap_id}", response_model=ResponseSchemaModel[Dict[str, Any]])
async def delete_roadmap(
    roadmap_id: str,
    db: CurrentSessionTransaction,  # ✅ 自动管理事务
    current_user: User = Depends(current_active_user),  # ✅ 从JWT获取用户
    service: CurrentManagementService = None,
) -> ResponseSchemaModel[Dict[str, Any]]:
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
            user_id=current_user.id  # ✅ 使用验证后的用户ID
        )
        
        # ✅ 自动 commit，无需手动调用
        
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


@router.post("/{roadmap_id}/restore", response_model=ResponseSchemaModel[Dict[str, Any]])
async def restore_roadmap(
    roadmap_id: str,
    db: CurrentSessionTransaction,  # ✅ 自动管理事务
    current_user: User = Depends(current_active_user),  # ✅ 从JWT获取用户
    service: CurrentManagementService = None,
) -> ResponseSchemaModel[Dict[str, Any]]:
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
            user_id=current_user.id  # ✅ 使用验证后的用户ID
        )
        
        # ✅ 自动 commit
        
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


@router.delete("/{roadmap_id}/permanent", response_model=ResponseSchemaModel[Dict[str, Any]])
async def permanently_delete_roadmap(
    roadmap_id: str,
    db: CurrentSessionTransaction,  # ✅ 自动管理事务
    current_user: User = Depends(current_active_user),  # ✅ 从JWT获取用户
    service: CurrentManagementService = None,
) -> ResponseSchemaModel[Dict[str, Any]]:
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
            user_id=current_user.id  # ✅ 使用验证后的用户ID
        )
        
        # ✅ 自动 commit
        
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
