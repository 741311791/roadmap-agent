"""
管理员 API 端点

提供用户邀请、Waitlist 管理、Tavily API Key管理等功能。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import EmailStr  # ✅ EmailStr 用于路由参数类型
import structlog

from app.db.session import get_db_transaction
from app.models.database import User
from app.core.auth.deps import current_superuser
from app.core.auth.user_manager import get_user_manager, UserManager
from app.services.email_service import get_email_service, EmailService
from app.services.admin import UserInviteService, TavilyKeyService, SuperuserService

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

@router.post("/invite-user", response_model=InviteUserResponse)
async def invite_user(
    request: InviteUserRequest,
    current_user: User = Depends(current_superuser),
    user_manager: UserManager = Depends(get_user_manager),
    email_service: EmailService = Depends(get_email_service),
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    邀请Waitlist用户
    
    为指定邮箱创建用户账号，生成临时密码。
    只有超级管理员可以调用。
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
        
        await db.commit()
        
        logger.info(
            "admin_invite_user_success",
            admin_id=current_user.id,
            email=request.email,
        )
        
        return InviteUserResponse(**result)
        
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error("admin_invite_user_failed", admin_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@router.get("/waitlist", response_model=WaitlistResponse)
async def get_waitlist(
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db_transaction),
    limit: int = 100,
    offset: int = 0,
    pending_only: bool = False,
):
    """
    获取Waitlist用户列表
    
    只有超级管理员可以查看。
    """
    service = UserInviteService()
    result = await service.get_waitlist(db, limit, offset, pending_only)
    
    return WaitlistResponse(
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
    )


@router.get("/waitlist-invites", response_model=WaitlistInviteListResponse)
async def get_waitlist_invites(
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db_transaction),
    limit: int = 100,
    offset: int = 0,
    status: str = "all",
):
    """
    获取Waitlist邀请列表（包含凭证信息）
    
    只有超级管理员可以查看。
    """
    service = UserInviteService()
    result = await service.get_waitlist_invites(db, limit, offset, status)
    
    logger.info(
        "admin_get_waitlist_invites",
        admin_id=current_user.id,
        status=status,
        total=result["total"],
    )
    
    return WaitlistInviteListResponse(
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
    )


@router.post("/waitlist-invites/batch-send", response_model=BatchSendInviteResponse)
async def batch_send_invites(
    request: BatchSendInviteRequest,
    current_user: User = Depends(current_superuser),
    user_manager: UserManager = Depends(get_user_manager),
    email_service: EmailService = Depends(get_email_service),
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    批量发送Waitlist邀请
    
    采用"一次读取，批量处理，部分提交"策略优化性能。
    只有超级管理员可以调用。
    """
    logger.info(
        "admin_batch_send_invites_requested",
        admin_id=current_user.id,
        email_count=len(request.emails),
    )
    
    service = UserInviteService()
    success_count, errors = await service.batch_send_invites(
        session=db,
        emails=request.emails,
        password_validity_days=request.password_validity_days,
        admin_user_id=current_user.id,
        user_manager=user_manager,
        email_service=email_service,
    )
    
    # 提交所有成功的变更
    if success_count > 0:
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error("admin_batch_send_invites_commit_failed", error=str(e))
            return BatchSendInviteResponse(success=0, failed=len(request.emails), errors=[
                {"email": email, "error": f"Final commit failed: {str(e)}"} 
                for email in request.emails
            ])
    
    return BatchSendInviteResponse(success=success_count, failed=len(errors), errors=errors)


# ============================================================
# 超级管理员端点
# ============================================================

@router.post("/create-superuser")
async def create_initial_superuser(
    email: EmailStr,
    password: str,
    db: AsyncSession = Depends(get_db_transaction),
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    创建初始超级管理员（仅在没有超级管理员时可用）
    
    这是一个初始化端点，只有当系统中没有超级管理员时才能调用。
    """
    try:
        service = SuperuserService()
        result = await service.create_initial_superuser(db, email, password, user_manager)
        await db.commit()
        return result
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error("create_superuser_failed", email=email, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create superuser: {str(e)}")


# ============================================================
# Tavily API Key端点
# ============================================================

@router.get("/tavily-keys", response_model=TavilyAPIKeyListResponse)
async def get_tavily_keys(
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    获取所有Tavily API Keys
    
    只有超级管理员可以查看。
    """
    try:
        service = TavilyKeyService()
        keys = await service.get_all_keys(db)
        
        logger.info("admin_get_tavily_keys", admin_id=current_user.id, total_keys=len(keys))
        
        return TavilyAPIKeyListResponse(
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
        )
    except Exception as e:
        logger.error("admin_get_tavily_keys_failed", admin_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get Tavily API Keys: {str(e)}")


@router.post("/tavily-keys", response_model=TavilyAPIKeyInfo)
async def add_tavily_key(
    request: AddTavilyAPIKeyRequest,
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    添加单个Tavily API Key
    
    只有超级管理员可以调用。
    """
    logger.info(
        "admin_add_tavily_key_requested",
        admin_id=current_user.id,
        key_prefix=request.api_key[:10] + "...",
    )
    
    try:
        service = TavilyKeyService()
        new_key = await service.add_key(db, request.api_key, request.plan_limit)
        await db.commit()
        
        logger.info("admin_add_tavily_key_success", admin_id=current_user.id)
        
        return TavilyAPIKeyInfo(
            api_key=f"{new_key.api_key[:10]}...{new_key.api_key[-4:]}" if len(new_key.api_key) > 14 else new_key.api_key,
            plan_limit=new_key.plan_limit,
            remaining_quota=new_key.remaining_quota,
            created_at=new_key.created_at.isoformat(),
            updated_at=new_key.updated_at.isoformat(),
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error("admin_add_tavily_key_failed", admin_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to add Tavily API Key: {str(e)}")


@router.post("/tavily-keys/batch", response_model=BatchAddTavilyKeysResponse)
async def batch_add_tavily_keys(
    request: BatchAddTavilyKeysRequest,
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    批量添加Tavily API Keys
    
    采用"一次读取，批量处理，一次提交"策略优化性能。
    只有超级管理员可以调用。
    """
    logger.info(
        "admin_batch_add_tavily_keys_requested",
        admin_id=current_user.id,
        key_count=len(request.keys),
    )
    
    service = TavilyKeyService()
    keys_data = [{"api_key": k.api_key, "plan_limit": k.plan_limit} for k in request.keys]
    success_count, errors = await service.batch_add_keys(db, keys_data)
    
    if success_count > 0:
        await db.commit()
    
    logger.info(
        "admin_batch_add_tavily_keys_completed",
        admin_id=current_user.id,
        success=success_count,
        failed=len(errors),
    )
    
    return BatchAddTavilyKeysResponse(success=success_count, failed=len(errors), errors=errors)


@router.put("/tavily-keys/{api_key}", response_model=TavilyAPIKeyInfo)
async def update_tavily_key(
    api_key: str,
    request: UpdateTavilyAPIKeyRequest,
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    更新Tavily API Key配额
    
    只有超级管理员可以调用。
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
        await db.commit()
        
        logger.info("admin_update_tavily_key_success", admin_id=current_user.id)
        
        return TavilyAPIKeyInfo(
            api_key=f"{updated_key.api_key[:10]}...{updated_key.api_key[-4:]}" if len(updated_key.api_key) > 14 else updated_key.api_key,
            plan_limit=updated_key.plan_limit,
            remaining_quota=updated_key.remaining_quota,
            created_at=updated_key.created_at.isoformat(),
            updated_at=updated_key.updated_at.isoformat(),
        )
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error("admin_update_tavily_key_failed", admin_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update Tavily API Key: {str(e)}")


@router.delete("/tavily-keys/{api_key}", response_model=DeleteTavilyAPIKeyResponse)
async def delete_tavily_key(
    api_key: str,
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db_transaction),
):
    """
    删除Tavily API Key
    
    只有超级管理员可以调用。
    """
    logger.info("admin_delete_tavily_key_requested", admin_id=current_user.id)
    
    try:
        service = TavilyKeyService()
        result = await service.delete_key(db, api_key)
        await db.commit()
        
        logger.info("admin_delete_tavily_key_success", admin_id=current_user.id)
        
        return DeleteTavilyAPIKeyResponse(**result)
    except ValueError as e:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await db.rollback()
        logger.error("admin_delete_tavily_key_failed", admin_id=current_user.id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete Tavily API Key: {str(e)}")
