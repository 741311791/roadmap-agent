"""
Tavily API Key管理 API 端点

提供Tavily API Key的批量管理功能。

重构变更：
- ✅ 从 admin.py 拆分出来
- ✅ 专注于Tavily Key批量管理功能
- ✅ 使用统一响应格式（ResponseSchemaModel）
- ✅ 批量更新通过Tavily官方API查询配额
"""
from fastapi import APIRouter, Depends
import structlog

from app.api.v1.deps import CurrentSession, CurrentSessionTransaction
from app.models.database import User
from app.core.auth.deps import current_superuser
from app.services.admin import TavilyKeyService
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base

# ✅ 导入 Schema
from app.schemas.admin import (
    TavilyAPIKeyInfo,
    TavilyAPIKeyListResponse,
    BatchAddTavilyKeysRequest,
    BatchAddTavilyKeysResponse,
    BatchUpdateTavilyKeysRequest,
    BatchUpdateTavilyKeysResponse,
    BatchDeleteTavilyKeysRequest,
    BatchDeleteTavilyKeysResponse,
)

router = APIRouter(prefix="/tavily", tags=["admin-tavily"])
logger = structlog.get_logger()


@router.get("/keys", response_model=ResponseSchemaModel[TavilyAPIKeyListResponse])
async def get_tavily_keys(
    db: CurrentSession,
    current_user: User = Depends(current_superuser),
) -> ResponseSchemaModel[TavilyAPIKeyListResponse]:
    """
    获取所有Tavily API Keys
    
    只有超级管理员可以查看。
    
    Args:
        db: 数据库会话
        current_user: 当前超级管理员
        
    Returns:
        API Key列表（脱敏显示）
    """
    try:
        service = TavilyKeyService()
        keys = await service.get_all_keys(db)
        
        logger.info("admin_get_tavily_keys", admin_id=current_user.id, total_keys=len(keys))
        
        return response_base.success(data=TavilyAPIKeyListResponse(
            keys=[
                TavilyAPIKeyInfo(
                    api_key=f"{key.api_key[:10]}...{key.api_key[-4:]}" if len(key.api_key) > 14 else key.api_key,
                    plan_limit=key.plan_limit,
                    remaining_quota=key.remaining_quota,
                    created_at=key.created_at.isoformat(),
                    updated_at=key.updated_at.isoformat(),
                )
                for key in keys
            ],
            total=len(keys),
        ))
        
    except Exception as e:
        logger.error("admin_get_tavily_keys_failed", admin_id=current_user.id, error=str(e))
        raise errors.InternalServerError(msg="获取API Keys失败")


@router.post("/keys/batch", response_model=ResponseSchemaModel[BatchAddTavilyKeysResponse])
async def batch_add_tavily_keys(
    request: BatchAddTavilyKeysRequest,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
) -> ResponseSchemaModel[BatchAddTavilyKeysResponse]:
    """
    批量添加Tavily API Keys
    
    采用"一次读取，批量处理，一次提交"策略优化性能。
    只有超级管理员可以调用。
    
    Args:
        request: 批量API Key请求
        db: 数据库会话（自动commit/rollback）
        current_user: 当前超级管理员
        
    Returns:
        批量操作结果
    """
    logger.info(
        "admin_batch_add_tavily_keys_requested",
        admin_id=current_user.id,
        key_count=len(request.keys),
    )
    
    service = TavilyKeyService()
    keys_data = [{"api_key": k.api_key, "plan_limit": k.plan_limit} for k in request.keys]
    success_count, errors_list = await service.batch_add_keys(db, keys_data)
    
    logger.info(
        "admin_batch_add_tavily_keys_completed",
        admin_id=current_user.id,
        success=success_count,
        failed=len(errors_list),
    )
    
    return response_base.success(data=BatchAddTavilyKeysResponse(
        success=success_count,
        failed=len(errors_list),
        errors=errors_list
    ))


@router.post("/keys/batch-update", response_model=ResponseSchemaModel[BatchUpdateTavilyKeysResponse])
async def batch_update_tavily_keys(
    request: BatchUpdateTavilyKeysRequest,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
) -> ResponseSchemaModel[BatchUpdateTavilyKeysResponse]:
    """
    批量更新Tavily API Keys配额（通过官方API查询）
    
    工作流程：
    1. 从数据库读取指定的API Keys
    2. 对每个Key调用Tavily官方API查询当前配额
    3. 更新数据库中的remaining_quota和plan_limit
    
    只有超级管理员可以调用。
    
    Args:
        request: 批量更新请求（包含待更新的API Keys列表）
        db: 数据库会话（自动commit/rollback）
        current_user: 当前超级管理员
        
    Returns:
        批量更新结果
    """
    logger.info(
        "admin_batch_update_tavily_keys_requested",
        admin_id=current_user.id,
        key_count=len(request.api_keys),
    )
    
    service = TavilyKeyService()
    success_count, errors_list = await service.batch_update_keys(db, request.api_keys)
    
    logger.info(
        "admin_batch_update_tavily_keys_completed",
        admin_id=current_user.id,
        success=success_count,
        failed=len(errors_list),
    )
    
    return response_base.success(data=BatchUpdateTavilyKeysResponse(
        success=success_count,
        failed=len(errors_list),
        errors=errors_list
    ))


@router.post("/keys/batch-delete", response_model=ResponseSchemaModel[BatchDeleteTavilyKeysResponse])
async def batch_delete_tavily_keys(
    request: BatchDeleteTavilyKeysRequest,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
) -> ResponseSchemaModel[BatchDeleteTavilyKeysResponse]:
    """
    批量删除Tavily API Keys
    
    采用"一次读取，批量删除，一次提交"策略优化性能。
    只有超级管理员可以调用。
    
    Args:
        request: 批量删除请求（包含待删除的API Keys列表）
        db: 数据库会话（自动commit/rollback）
        current_user: 当前超级管理员
        
    Returns:
        批量删除结果
    """
    logger.info(
        "admin_batch_delete_tavily_keys_requested",
        admin_id=current_user.id,
        key_count=len(request.api_keys),
    )
    
    service = TavilyKeyService()
    success_count, errors_list = await service.batch_delete_keys(db, request.api_keys)
    
    logger.info(
        "admin_batch_delete_tavily_keys_completed",
        admin_id=current_user.id,
        success=success_count,
        failed=len(errors_list),
    )
    
    return response_base.success(data=BatchDeleteTavilyKeysResponse(
        success=success_count,
        failed=len(errors_list),
        errors=errors_list
    ))


@router.post("/keys/refresh-quota", response_model=ResponseSchemaModel[BatchUpdateTavilyKeysResponse])
async def refresh_all_tavily_keys_quota(
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
) -> ResponseSchemaModel[BatchUpdateTavilyKeysResponse]:
    """
    刷新所有Tavily API Keys的配额信息
    
    自动获取数据库中所有的API Keys，并通过Tavily官方API查询最新配额。
    只有超级管理员可以调用。
    
    Args:
        db: 数据库会话（自动commit/rollback）
        current_user: 当前超级管理员
        
    Returns:
        批量更新结果
    """
    logger.info(
        "admin_refresh_all_tavily_keys_requested",
        admin_id=current_user.id,
    )
    
    service = TavilyKeyService()
    
    # 获取所有API Keys
    all_keys = await service.get_all_keys(db)
    
    if not all_keys:
        logger.warning(
            "admin_refresh_all_tavily_keys_no_keys",
            admin_id=current_user.id,
        )
        return response_base.success(data=BatchUpdateTavilyKeysResponse(
            success=0,
            failed=0,
            errors=[]
        ))
    
    # 提取API Key列表
    api_keys_list = [key.api_key for key in all_keys]
    
    logger.info(
        "admin_refresh_all_tavily_keys_processing",
        admin_id=current_user.id,
        total_keys=len(api_keys_list),
    )
    
    # 批量更新配额
    success_count, errors_list = await service.batch_update_keys(db, api_keys_list)
    
    logger.info(
        "admin_refresh_all_tavily_keys_completed",
        admin_id=current_user.id,
        total_keys=len(api_keys_list),
        success=success_count,
        failed=len(errors_list),
    )
    
    return response_base.success(data=BatchUpdateTavilyKeysResponse(
        success=success_count,
        failed=len(errors_list),
        errors=errors_list
    ))

