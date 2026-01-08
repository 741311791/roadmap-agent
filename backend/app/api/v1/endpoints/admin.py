"""
管理员 API 端点

提供用户邀请、Waitlist 管理、Tavily API Key管理等功能。

重构说明：
- ✅ 使用 CurrentSession/CurrentSessionTransaction 自动管理事务
- ✅ 使用自定义异常替代 HTTPException
- ✅ 使用统一响应格式（ResponseSchemaModel）
- ✅ 符合企业级架构规范
"""
from fastapi import APIRouter, Depends
from pydantic import EmailStr
import structlog

from app.api.v1.deps import CurrentSession, CurrentSessionTransaction
from app.models.database import User
from app.core.auth.deps import current_superuser
from app.core.auth.user_manager import get_user_manager, UserManager
from app.services.email_service import get_email_service, EmailService
from app.services.admin import UserInviteService, TavilyKeyService, SuperuserService
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base

# ✅ 导入 Schema（符合企业级架构规范）
from app.schemas.admin import (
    InviteUserRequest,
    InviteUserResponse,
    WaitlistUserInfo,
    WaitlistResponse,
    WaitlistInviteItem,
    WaitlistInviteListResponse,
    BatchSendInviteRequest,
    BatchSendInviteResponse,
    TavilyAPIKeyInfo,
    TavilyAPIKeyListResponse,
    AddTavilyAPIKeyRequest,
    BatchAddTavilyKeysRequest,
    BatchAddTavilyKeysResponse,
    UpdateTavilyAPIKeyRequest,
    DeleteTavilyAPIKeyResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])
logger = structlog.get_logger()


# ============================================================
# 用户邀请端点
# ============================================================

@router.post("/invite-user", response_model=ResponseSchemaModel[InviteUserResponse])
async def invite_user(
    request: InviteUserRequest,
    db: CurrentSessionTransaction,  # ✅ 自动管理事务
    current_user: User = Depends(current_superuser),
    user_manager: UserManager = Depends(get_user_manager),
    email_service: EmailService = Depends(get_email_service),
) -> ResponseSchemaModel[InviteUserResponse]:
    """
    邀请Waitlist用户
    
    为指定邮箱创建用户账号，生成临时密码。
    只有超级管理员可以调用。
    
    Args:
        request: 邀请请求（包含邮箱、密码有效期等）
        db: 数据库会话（自动commit/rollback）
        current_user: 当前超级管理员
        user_manager: 用户管理器
        email_service: 邮件服务
        
    Returns:
        邀请结果（包含用户名、密码等）
        
    Raises:
        RequestError: 请求参数错误
        InternalServerError: 服务器内部错误
    """
    logger.info(
        "admin_invite_user_requested",
        admin_id=current_user.id,
        target_email=request.email,
    )
    
    try:
        service = UserInviteService()
        result = await service.invite_single_user(
            session=db,
            email=request.email,
            password_validity_days=request.password_validity_days,
            user_manager=user_manager,
            email_service=email_service if request.send_email else None,
            send_email=request.send_email,
        )
        
        # ✅ 自动 commit，无需手动调用
        
        logger.info(
            "admin_invite_user_success",
            admin_id=current_user.id,
            email=request.email,
        )
        
        return response_base.success(data=InviteUserResponse(**result))
        
    except ValueError as e:
        # ✅ 使用自定义异常替代 HTTPException
        raise errors.RequestError(msg=str(e))
    except Exception as e:
        logger.error("admin_invite_user_failed", admin_id=current_user.id, error=str(e))
        raise errors.InternalServerError(msg=f"用户创建失败: {str(e)}")


@router.get("/waitlist", response_model=ResponseSchemaModel[WaitlistResponse])
async def get_waitlist(
    db: CurrentSession,  # ✅ 读操作使用 CurrentSession
    current_user: User = Depends(current_superuser),
    limit: int = 100,
    offset: int = 0,
    pending_only: bool = False,
) -> ResponseSchemaModel[WaitlistResponse]:
    """
    获取Waitlist用户列表
    
    只有超级管理员可以查看。
    
    Args:
        db: 数据库会话
        current_user: 当前超级管理员
        limit: 返回数量限制
        offset: 分页偏移
        pending_only: 是否只返回待邀请的用户
        
    Returns:
        Waitlist用户列表
    """
    service = UserInviteService()
    result = await service.get_waitlist(db, limit, offset, pending_only)
    
    return response_base.success(data=WaitlistResponse(
        users=[
            WaitlistUserInfo(
                email=u.email,
                source=u.source,
                invited=u.invited,
                invited_at=u.invited_at.isoformat() if u.invited_at else None,
                created_at=u.created_at.isoformat(),
            )
            for u in result["users"]
        ],
        total=result["total"],
        pending=result["pending"],
        invited=result["invited"],
    ))


@router.get("/waitlist-invites", response_model=ResponseSchemaModel[WaitlistInviteListResponse])
async def get_waitlist_invites(
    db: CurrentSession,  # ✅ 读操作使用 CurrentSession
    current_user: User = Depends(current_superuser),
    limit: int = 100,
    offset: int = 0,
    status: str = "all",
) -> ResponseSchemaModel[WaitlistInviteListResponse]:
    """
    获取Waitlist邀请列表（包含凭证信息）
    
    只有超级管理员可以查看。
    
    Args:
        db: 数据库会话
        current_user: 当前超级管理员
        limit: 返回数量限制
        offset: 分页偏移
        status: 状态筛选
        
    Returns:
        邀请列表（包含用户名、密码等敏感信息）
    """
    service = UserInviteService()
    result = await service.get_waitlist_invites(db, limit, offset, status)
    
    logger.info(
        "admin_get_waitlist_invites",
        admin_id=current_user.id,
        status=status,
        total=result["total"],
    )
    
    return response_base.success(data=WaitlistInviteListResponse(
        items=[
            WaitlistInviteItem(
                email=item.email,
                source=item.source,
                invited=item.invited,
                invited_at=item.invited_at.isoformat() if item.invited_at else None,
                created_at=item.created_at.isoformat(),
                username=item.username,
                password=item.password,
                expires_at=item.expires_at.isoformat() if item.expires_at else None,
                sent_content=item.sent_content,
            )
            for item in result["items"]
        ],
        total=result["total"],
        pending=result["pending"],
        invited=result["invited"],
    ))


@router.post("/waitlist-invites/batch-send", response_model=ResponseSchemaModel[BatchSendInviteResponse])
async def batch_send_invites(
    request: BatchSendInviteRequest,
    db: CurrentSessionTransaction,  # ✅ 写操作使用 CurrentSessionTransaction
    current_user: User = Depends(current_superuser),
    user_manager: UserManager = Depends(get_user_manager),
    email_service: EmailService = Depends(get_email_service),
) -> ResponseSchemaModel[BatchSendInviteResponse]:
    """
    批量发送Waitlist邀请
    
    采用"一次读取，批量处理，部分提交"策略优化性能。
    只有超级管理员可以调用。
    
    Args:
        request: 批量邀请请求
        db: 数据库会话（自动commit/rollback）
        current_user: 当前超级管理员
        user_manager: 用户管理器
        email_service: 邮件服务
        
    Returns:
        批量操作结果（成功数、失败数、错误详情）
    """
    logger.info(
        "admin_batch_send_invites_requested",
        admin_id=current_user.id,
        email_count=len(request.emails),
    )
    
    try:
        service = UserInviteService()
        success_count, errors_list = await service.batch_send_invites(
            session=db,
            emails=request.emails,
            password_validity_days=request.password_validity_days,
            admin_user_id=current_user.id,
            user_manager=user_manager,
            email_service=email_service,
        )
        
        # ✅ 自动 commit，无需手动调用
        
        return response_base.success(data=BatchSendInviteResponse(
            success=success_count,
            failed=len(errors_list),
            errors=errors_list
        ))
        
    except Exception as e:
        logger.error("admin_batch_send_invites_failed", error=str(e))
        raise errors.InternalServerError(msg="批量邀请失败")


# ============================================================
# 超级管理员端点
# ============================================================

@router.post("/create-superuser")
async def create_initial_superuser(
    email: EmailStr,
    password: str,
    db: CurrentSessionTransaction,  # ✅ 写操作使用 CurrentSessionTransaction
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    创建初始超级管理员（仅在没有超级管理员时可用）
    
    这是一个初始化端点，只有当系统中没有超级管理员时才能调用。
    
    Args:
        email: 管理员邮箱
        password: 管理员密码
        db: 数据库会话（自动commit/rollback）
        user_manager: 用户管理器
        
    Returns:
        创建结果
        
    Raises:
        RequestError: 已存在超级管理员或参数错误
        InternalServerError: 创建失败
    """
    try:
        service = SuperuserService()
        result = await service.create_initial_superuser(db, email, password, user_manager)
        
        # ✅ 自动 commit
        
        return response_base.success(data=result)
        
    except ValueError as e:
        raise errors.RequestError(msg=str(e))
    except Exception as e:
        logger.error("create_superuser_failed", email=email, error=str(e))
        raise errors.InternalServerError(msg=f"超级管理员创建失败: {str(e)}")


# ============================================================
# Tavily API Key端点
# ============================================================

@router.get("/tavily-keys", response_model=ResponseSchemaModel[TavilyAPIKeyListResponse])
async def get_tavily_keys(
    db: CurrentSession,  # ✅ 读操作使用 CurrentSession
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


@router.post("/tavily-keys", response_model=ResponseSchemaModel[TavilyAPIKeyInfo])
async def add_tavily_key(
    request: AddTavilyAPIKeyRequest,
    db: CurrentSessionTransaction,  # ✅ 写操作使用 CurrentSessionTransaction
    current_user: User = Depends(current_superuser),
) -> ResponseSchemaModel[TavilyAPIKeyInfo]:
    """
    添加单个Tavily API Key
    
    只有超级管理员可以调用。
    
    Args:
        request: API Key信息
        db: 数据库会话（自动commit/rollback）
        current_user: 当前超级管理员
        
    Returns:
        添加成功的API Key信息
        
    Raises:
        RequestError: API Key已存在或参数错误
        InternalServerError: 添加失败
    """
    logger.info(
        "admin_add_tavily_key_requested",
        admin_id=current_user.id,
        key_prefix=request.api_key[:10] + "...",
    )
    
    try:
        service = TavilyKeyService()
        new_key = await service.add_key(db, request.api_key, request.plan_limit)
        
        # ✅ 自动 commit
        
        logger.info("admin_add_tavily_key_success", admin_id=current_user.id)
        
        return response_base.success(data=TavilyAPIKeyInfo(
            api_key=f"{new_key.api_key[:10]}...{new_key.api_key[-4:]}" if len(new_key.api_key) > 14 else new_key.api_key,
            plan_limit=new_key.plan_limit,
            remaining_quota=new_key.remaining_quota,
            created_at=new_key.created_at.isoformat(),
            updated_at=new_key.updated_at.isoformat(),
        ))
        
    except ValueError as e:
        raise errors.RequestError(msg=str(e))
    except Exception as e:
        logger.error("admin_add_tavily_key_failed", admin_id=current_user.id, error=str(e))
        raise errors.InternalServerError(msg="添加API Key失败")


@router.post("/tavily-keys/batch", response_model=ResponseSchemaModel[BatchAddTavilyKeysResponse])
async def batch_add_tavily_keys(
    request: BatchAddTavilyKeysRequest,
    db: CurrentSessionTransaction,  # ✅ 写操作使用 CurrentSessionTransaction
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
    
    # ✅ 自动 commit
    
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


@router.put("/tavily-keys/{api_key}", response_model=ResponseSchemaModel[TavilyAPIKeyInfo])
async def update_tavily_key(
    api_key: str,
    request: UpdateTavilyAPIKeyRequest,
    db: CurrentSessionTransaction,  # ✅ 写操作使用 CurrentSessionTransaction
    current_user: User = Depends(current_superuser),
) -> ResponseSchemaModel[TavilyAPIKeyInfo]:
    """
    更新Tavily API Key配额
    
    只有超级管理员可以调用。
    
    Args:
        api_key: API Key（URL路径参数）
        request: 更新请求
        db: 数据库会话（自动commit/rollback）
        current_user: 当前超级管理员
        
    Returns:
        更新后的API Key信息
        
    Raises:
        NotFoundError: API Key不存在
        InternalServerError: 更新失败
    """
    logger.info("admin_update_tavily_key_requested", admin_id=current_user.id)
    
    try:
        service = TavilyKeyService()
        updated_key = await service.update_key(
            db,
            api_key,
            request.remaining_quota,
            request.plan_limit,
        )
        
        # ✅ 自动 commit
        
        logger.info("admin_update_tavily_key_success", admin_id=current_user.id)
        
        return response_base.success(data=TavilyAPIKeyInfo(
            api_key=f"{updated_key.api_key[:10]}...{updated_key.api_key[-4:]}" if len(updated_key.api_key) > 14 else updated_key.api_key,
            plan_limit=updated_key.plan_limit,
            remaining_quota=updated_key.remaining_quota,
            created_at=updated_key.created_at.isoformat(),
            updated_at=updated_key.updated_at.isoformat(),
        ))
        
    except ValueError as e:
        raise errors.NotFoundError(msg=str(e))
    except Exception as e:
        logger.error("admin_update_tavily_key_failed", admin_id=current_user.id, error=str(e))
        raise errors.InternalServerError(msg="更新API Key失败")


@router.delete("/tavily-keys/{api_key}", response_model=ResponseSchemaModel[DeleteTavilyAPIKeyResponse])
async def delete_tavily_key(
    api_key: str,
    db: CurrentSessionTransaction,  # ✅ 写操作使用 CurrentSessionTransaction
    current_user: User = Depends(current_superuser),
) -> ResponseSchemaModel[DeleteTavilyAPIKeyResponse]:
    """
    删除Tavily API Key
    
    只有超级管理员可以调用。
    
    Args:
        api_key: API Key（URL路径参数）
        db: 数据库会话（自动commit/rollback）
        current_user: 当前超级管理员
        
    Returns:
        删除结果
        
    Raises:
        NotFoundError: API Key不存在
        InternalServerError: 删除失败
    """
    logger.info("admin_delete_tavily_key_requested", admin_id=current_user.id)
    
    try:
        service = TavilyKeyService()
        result = await service.delete_key(db, api_key)
        
        # ✅ 自动 commit
        
        logger.info("admin_delete_tavily_key_success", admin_id=current_user.id)
        
        return response_base.success(data=DeleteTavilyAPIKeyResponse(**result))
        
    except ValueError as e:
        raise errors.NotFoundError(msg=str(e))
    except Exception as e:
        logger.error("admin_delete_tavily_key_failed", admin_id=current_user.id, error=str(e))
        raise errors.InternalServerError(msg="删除API Key失败")
