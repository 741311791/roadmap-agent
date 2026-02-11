"""
Waitlist管理 API 端点

提供候补名单的加入（公开）和管理（管理员）功能。

重构变更：
- ✅ 合并 users/waitlist.py 和 admin/admin.py 中的Waitlist相关接口
- ✅ 拆分为公开接口和管理员接口
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from typing import Dict, Any
from fastapi import APIRouter, Depends
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

from app.api.v1.deps import CurrentSession, CurrentSessionTransaction
from app.models.database import User, WaitlistEmail, beijing_now
from app.core.auth.deps import current_superuser
from app.core.auth.user_manager import get_user_manager, UserManager
from app.services.shared.email_service import get_email_service, EmailService
from app.services.admin import UserInviteService
from app.core.custom_exceptions import errors
from app.core.response_schema import ResponseSchemaModel, response_base

# ✅ 导入 Schema
from app.schemas.waitlist import (
    WaitlistJoinRequest,
    WaitlistJoinResponse,
)
from app.schemas.admin import (
    WaitlistUserInfo,
    WaitlistResponse,
    WaitlistInviteItem,
    WaitlistInviteListResponse,
    BatchSendInviteRequest,
    BatchSendInviteResponse,
)

logger = structlog.get_logger()


# ============================================================
# 公开端点（无需认证）
# ============================================================

router_public = APIRouter(prefix="/waitlist", tags=["waitlist-public"])


@router_public.post("", response_model=ResponseSchemaModel[WaitlistJoinResponse])
async def join_waitlist(
    request: WaitlistJoinRequest,
    db: CurrentSessionTransaction,
) -> ResponseSchemaModel[WaitlistJoinResponse]:
    """
    加入候补名单（公开接口，无需认证）
    
    用户在首页提交邮箱后调用此接口，将邮箱存入候补名单。
    如果邮箱已存在，返回成功但标记为非新用户。
    
    Args:
        request: 包含邮箱和来源的请求体
        db: 数据库会话（自动commit/rollback）
        
    Returns:
        加入结果，包含成功标志和是否为新用户
    """
    email = request.email.lower().strip()
    
    logger.info(
        "waitlist_join_requested",
        email=email,
        source=request.source,
    )
    
    # 检查邮箱是否已存在
    result = await db.execute(
        select(WaitlistEmail).where(WaitlistEmail.email == email)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        # 计算该用户在候补名单中的位置
        count_result = await db.execute(
            select(func.count()).select_from(WaitlistEmail).where(
                WaitlistEmail.created_at <= existing.created_at
            )
        )
        position = count_result.scalar_one()
        
        logger.info("waitlist_email_already_exists", email=email, position=position)
        return response_base.success(data=WaitlistJoinResponse(
            success=True,
            message="You're already on our waitlist! We'll be in touch soon.",
            is_new=False,
            position=position,
        ))
    
    # 创建新记录
    waitlist_entry = WaitlistEmail(
        email=email,
        source=request.source,
        invited=False,
        invited_at=None,
        created_at=beijing_now(),
    )
    
    db.add(waitlist_entry)
    await db.flush()  # 获取ID和created_at
    
    # 计算新用户在候补名单中的位置
    count_result = await db.execute(
        select(func.count()).select_from(WaitlistEmail).where(
            WaitlistEmail.created_at <= waitlist_entry.created_at
        )
    )
    position = count_result.scalar_one()
    
    logger.info(
        "waitlist_email_added",
        email=email,
        source=request.source,
        position=position,
    )
    
    return response_base.success(data=WaitlistJoinResponse(
        success=True,
        message="Thank you for joining our waitlist! We'll notify you when access is available.",
        is_new=True,
        position=position,
    ))


@router_public.get("/count", response_model=ResponseSchemaModel[Dict[str, Any]])
async def get_waitlist_count(
    db: CurrentSession,
) -> ResponseSchemaModel[Dict[str, Any]]:
    """
    获取候补名单人数（公开接口）
    
    Args:
        db: 数据库会话
        
    Returns:
        候补名单统计信息
    """
    # 总人数
    total_result = await db.execute(
        select(func.count()).select_from(WaitlistEmail)
    )
    total = total_result.scalar() or 0
    
    # 已邀请人数
    invited_result = await db.execute(
        select(func.count()).select_from(WaitlistEmail).where(WaitlistEmail.invited == True)
    )
    invited = invited_result.scalar() or 0
    
    return response_base.success(data={
        "total": total,
        "invited": invited,
        "pending": total - invited,
    })


# ============================================================
# 管理员端点（需要超级管理员权限）
# ============================================================

router_admin = APIRouter(tags=["admin-waitlist"])


@router_admin.get("/waitlist", response_model=ResponseSchemaModel[WaitlistResponse])
async def get_waitlist(
    db: CurrentSession,
    current_user: User = Depends(current_superuser),
    limit: int = 100,
    offset: int = 0,
    pending_only: bool = False,
) -> ResponseSchemaModel[WaitlistResponse]:
    """
    获取Waitlist用户列表（管理员）
    
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


@router_admin.get("/waitlist-invites", response_model=ResponseSchemaModel[WaitlistInviteListResponse])
async def get_waitlist_invites(
    db: CurrentSession,
    current_user: User = Depends(current_superuser),
    limit: int = 100,
    offset: int = 0,
    status: str = "all",
) -> ResponseSchemaModel[WaitlistInviteListResponse]:
    """
    获取Waitlist邀请列表（包含凭证信息，管理员）
    
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


@router_admin.post("/waitlist-invites/batch-send", response_model=ResponseSchemaModel[BatchSendInviteResponse])
async def batch_send_invites(
    request: BatchSendInviteRequest,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
    user_manager: UserManager = Depends(get_user_manager),
    email_service: EmailService = Depends(get_email_service),
) -> ResponseSchemaModel[BatchSendInviteResponse]:
    """
    批量发送Waitlist邀请（管理员）
    
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
        
        return response_base.success(data=BatchSendInviteResponse(
            success=success_count,
            failed=len(errors_list),
            errors=errors_list
        ))
        
    except Exception as e:
        logger.error("admin_batch_send_invites_failed", error=str(e))
        raise errors.InternalServerError(msg="批量邀请失败")


@router_admin.post("/create-superuser")
async def create_initial_superuser(
    email: EmailStr,
    password: str,
    db: CurrentSessionTransaction,
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
        
        return response_base.success(data=result)
        
    except ValueError as e:
        raise errors.RequestError(msg=str(e))
    except Exception as e:
        logger.error("create_superuser_failed", email=email, error=str(e))
        raise errors.InternalServerError(msg=f"超级管理员创建失败: {str(e)}")

