"""
管理员 API 端点

提供用户邀请、Waitlist 管理等管理功能。
"""
import secrets
import string
from datetime import timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr
import structlog

from app.db.session import get_db
from app.models.database import User, WaitlistEmail, beijing_now
from app.core.auth.deps import current_superuser
from app.core.auth.user_manager import get_user_manager, UserManager
from app.core.auth.schemas import UserCreate
from app.services.email_service import get_email_service, EmailService

router = APIRouter(prefix="/admin", tags=["admin"])
logger = structlog.get_logger()


# ============================================================
# 请求/响应模型
# ============================================================

class InviteUserRequest(BaseModel):
    """
    邀请用户请求
    
    Args:
        email: 要邀请的用户邮箱
        password_validity_days: 临时密码有效期（天），默认 30 天
        send_email: 是否发送邀请邮件，默认 True
    """
    email: EmailStr
    password_validity_days: int = 30
    send_email: bool = True


class InviteUserResponse(BaseModel):
    """
    邀请用户响应
    
    Args:
        success: 是否成功
        email: 用户邮箱
        username: 生成的用户名
        temp_password: 临时密码（仅返回一次，请妥善保存）
        expires_at: 密码过期时间
        message: 提示消息
    """
    success: bool
    email: str
    username: str
    temp_password: str
    expires_at: str
    message: str


class WaitlistUserInfo(BaseModel):
    """
    Waitlist 用户信息
    
    Args:
        email: 用户邮箱
        source: 来源
        invited: 是否已邀请
        invited_at: 邀请时间
        created_at: 加入时间
    """
    email: str
    source: str
    invited: bool
    invited_at: Optional[str] = None
    created_at: str


class WaitlistResponse(BaseModel):
    """
    Waitlist 列表响应
    
    Args:
        users: 用户列表
        total: 总数
        pending: 待邀请数
        invited: 已邀请数
    """
    users: List[WaitlistUserInfo]
    total: int
    pending: int
    invited: int


class WaitlistInviteItem(BaseModel):
    """
    Waitlist 邀请列表项（包含凭证信息）
    
    Args:
        email: 用户邮箱
        source: 来源
        invited: 是否已邀请
        invited_at: 邀请时间
        created_at: 加入时间
        username: 生成的用户名
        password: 临时密码（仅管理员可见）
        expires_at: 密码过期时间
        sent_content: 发送历史记录
    """
    email: str
    source: str
    invited: bool
    invited_at: Optional[str] = None
    created_at: str
    username: Optional[str] = None
    password: Optional[str] = None
    expires_at: Optional[str] = None
    sent_content: Optional[dict] = None


class WaitlistInviteListResponse(BaseModel):
    """
    Waitlist 邀请列表响应
    
    Args:
        items: 邀请列表项
        total: 总数
        pending: 待邀请数
        invited: 已邀请数
    """
    items: List[WaitlistInviteItem]
    total: int
    pending: int
    invited: int


class BatchSendInviteRequest(BaseModel):
    """
    批量发送邀请请求
    
    Args:
        emails: 要发送邀请的邮箱列表
        password_validity_days: 密码有效期（天），默认 30 天
    """
    emails: List[str]
    password_validity_days: int = 30


class BatchSendInviteResponse(BaseModel):
    """
    批量发送响应
    
    Args:
        success: 成功发送的数量
        failed: 失败的数量
        errors: 失败详情列表
    """
    success: int
    failed: int
    errors: List[dict]


# ============================================================
# 工具函数
# ============================================================

def generate_random_password(length: int = 12) -> str:
    """
    生成随机临时密码
    
    密码包含大小写字母、数字，不包含容易混淆的字符（如 0/O, 1/l）。
    
    Args:
        length: 密码长度
        
    Returns:
        随机密码字符串
    """
    # 排除容易混淆的字符
    alphabet = string.ascii_letters + string.digits
    alphabet = alphabet.replace('0', '').replace('O', '').replace('o', '')
    alphabet = alphabet.replace('1', '').replace('l', '').replace('I', '')
    
    return ''.join(secrets.choice(alphabet) for _ in range(length))


# ============================================================
# API 端点
# ============================================================

@router.post("/invite-user", response_model=InviteUserResponse)
async def invite_user(
    request: InviteUserRequest,
    current_user: User = Depends(current_superuser),
    user_manager: UserManager = Depends(get_user_manager),
    email_service: EmailService = Depends(get_email_service),
    db: AsyncSession = Depends(get_db),
):
    """
    邀请 Waitlist 用户
    
    为指定邮箱创建用户账号，生成临时密码。
    只有超级管理员可以调用此接口。
    
    注意：
    - 临时密码仅返回一次，请妥善保存并发送给用户
    - 密码会在指定天数后过期
    - 如果用户已存在，会返回错误
    
    Args:
        request: 邀请请求，包含邮箱和密码有效期
        
    Returns:
        邀请结果，包含临时密码
    """
    email = request.email.lower().strip()
    
    logger.info(
        "admin_invite_user_requested",
        admin_id=current_user.id,
        target_email=email,
        validity_days=request.password_validity_days,
    )
    
    # 检查用户是否已存在
    existing_user = await db.execute(
        select(User).where(User.email == email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"User with email {email} already exists"
        )
    
    # 生成临时密码
    temp_password = generate_random_password()
    
    # 生成用户名（从邮箱提取）
    username = email.split('@')[0]
    
    # 计算密码过期时间
    expires_at = beijing_now() + timedelta(days=request.password_validity_days)
    
    # 创建用户
    user_create = UserCreate(
        email=email,
        username=username,
        password=temp_password,
    )
    
    try:
        new_user = await user_manager.create(user_create)
        
        # 设置密码过期时间
        new_user.password_expires_at = expires_at
        await db.commit()
        
        # 更新 Waitlist 记录（如果存在）
        waitlist_result = await db.execute(
            select(WaitlistEmail).where(WaitlistEmail.email == email)
        )
        waitlist_entry = waitlist_result.scalar_one_or_none()
        if waitlist_entry:
            waitlist_entry.invited = True
            waitlist_entry.invited_at = beijing_now()
            await db.commit()
        
        logger.info(
            "admin_invite_user_success",
            admin_id=current_user.id,
            new_user_id=new_user.id,
            email=email,
            expires_at=expires_at.isoformat(),
        )
        
        # 发送邀请邮件
        email_sent = False
        if request.send_email:
            email_sent = await email_service.send_invite_email(
                to_email=email,
                temp_password=temp_password,
                expires_at=expires_at,
                username=username,
            )
        
        message = f"User created successfully. Password expires on {expires_at.strftime('%Y-%m-%d %H:%M')} (Beijing Time)."
        if request.send_email:
            message += " Invitation email sent." if email_sent else " Failed to send invitation email."
        
        return InviteUserResponse(
            success=True,
            email=email,
            username=username,
            temp_password=temp_password,
            expires_at=expires_at.isoformat(),
            message=message
        )
        
    except Exception as e:
        logger.error(
            "admin_invite_user_failed",
            admin_id=current_user.id,
            email=email,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user: {str(e)}"
        )


@router.get("/waitlist", response_model=WaitlistResponse)
async def get_waitlist(
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
    pending_only: bool = False,
):
    """
    获取 Waitlist 用户列表
    
    只有超级管理员可以查看。
    
    Args:
        limit: 每页数量
        offset: 偏移量
        pending_only: 是否只显示未邀请的用户
        
    Returns:
        Waitlist 用户列表和统计信息
    """
    # 构建查询
    query = select(WaitlistEmail)
    if pending_only:
        query = query.where(WaitlistEmail.invited == False)
    query = query.order_by(WaitlistEmail.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    # 统计信息
    total_result = await db.execute(
        select(func.count()).select_from(WaitlistEmail)
    )
    total = total_result.scalar() or 0
    
    invited_result = await db.execute(
        select(func.count()).select_from(WaitlistEmail).where(WaitlistEmail.invited == True)
    )
    invited = invited_result.scalar() or 0
    
    return WaitlistResponse(
        users=[
            WaitlistUserInfo(
                email=u.email,
                source=u.source,
                invited=u.invited,
                invited_at=u.invited_at.isoformat() if u.invited_at else None,
                created_at=u.created_at.isoformat(),
            )
            for u in users
        ],
        total=total,
        pending=total - invited,
        invited=invited,
    )


@router.get("/waitlist-invites", response_model=WaitlistInviteListResponse)
async def get_waitlist_invites(
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
    status: str = "all",
):
    """
    获取 Waitlist 邀请列表（包含凭证信息）
    
    只有超级管理员可以查看。
    
    Args:
        limit: 每页数量
        offset: 偏移量
        status: 过滤状态 - all: 全部, pending: 未邀请, invited: 已邀请
        
    Returns:
        Waitlist 邀请列表和统计信息
    """
    # 构建查询
    query = select(WaitlistEmail)
    if status == "pending":
        query = query.where(WaitlistEmail.invited == False)
    elif status == "invited":
        query = query.where(WaitlistEmail.invited == True)
    
    query = query.order_by(WaitlistEmail.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    # 统计信息
    total_result = await db.execute(
        select(func.count()).select_from(WaitlistEmail)
    )
    total = total_result.scalar() or 0
    
    invited_result = await db.execute(
        select(func.count()).select_from(WaitlistEmail).where(WaitlistEmail.invited == True)
    )
    invited = invited_result.scalar() or 0
    
    logger.info(
        "admin_get_waitlist_invites",
        admin_id=current_user.id,
        status=status,
        total=total,
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
            for item in items
        ],
        total=total,
        pending=total - invited,
        invited=invited,
    )


@router.post("/waitlist-invites/batch-send", response_model=BatchSendInviteResponse)
async def batch_send_invites(
    request: BatchSendInviteRequest,
    current_user: User = Depends(current_superuser),
    user_manager: UserManager = Depends(get_user_manager),
    email_service: EmailService = Depends(get_email_service),
    db: AsyncSession = Depends(get_db),
):
    """
    批量发送 Waitlist 邀请
    
    为选中的邮箱生成临时凭证并发送邀请邮件。
    支持部分成功模式：成功的更新状态，失败的收集错误信息。
    
    只有超级管理员可以调用此接口。
    
    Args:
        request: 批量发送请求，包含邮箱列表和密码有效期
        
    Returns:
        批量发送结果，包含成功/失败数量和错误详情
    """
    logger.info(
        "admin_batch_send_invites_requested",
        admin_id=current_user.id,
        email_count=len(request.emails),
        validity_days=request.password_validity_days,
    )
    
    success_count = 0
    failed_count = 0
    errors = []
    
    for email_raw in request.emails:
        email = email_raw.lower().strip()
        
        try:
            # 检查 waitlist 记录是否存在
            waitlist_result = await db.execute(
                select(WaitlistEmail).where(WaitlistEmail.email == email)
            )
            waitlist_entry = waitlist_result.scalar_one_or_none()
            
            if not waitlist_entry:
                errors.append({
                    "email": email,
                    "error": "Email not found in waitlist"
                })
                failed_count += 1
                continue
            
            # 如果已经发送过，跳过
            if waitlist_entry.invited:
                errors.append({
                    "email": email,
                    "error": "Invitation already sent"
                })
                failed_count += 1
                continue
            
            # 检查用户是否已存在
            existing_user_result = await db.execute(
                select(User).where(User.email == email)
            )
            existing_user = existing_user_result.scalar_one_or_none()
            
            if existing_user:
                errors.append({
                    "email": email,
                    "error": "User account already exists"
                })
                failed_count += 1
                continue
            
            # 生成用户名（从邮箱提取）
            username = email.split('@')[0]
            
            # 生成临时密码
            temp_password = generate_random_password()
            
            # 计算密码过期时间
            expires_at = beijing_now() + timedelta(days=request.password_validity_days)
            
            # 创建用户账号
            try:
                user_create = UserCreate(
                    email=email,
                    username=username,
                    password=temp_password,
                )
                new_user = await user_manager.create(user_create)
                
                # 设置密码过期时间（不立即提交）
                new_user.password_expires_at = expires_at
                
            except Exception as user_create_error:
                errors.append({
                    "email": email,
                    "error": f"Failed to create user account: {str(user_create_error)}"
                })
                failed_count += 1
                await db.rollback()
                continue
            
            # 更新 waitlist 记录（不立即提交）
            waitlist_entry.username = username
            waitlist_entry.password = temp_password
            waitlist_entry.expires_at = expires_at
            
            # 发送邀请邮件
            email_sent = await email_service.send_invite_email(
                to_email=email,
                temp_password=temp_password,
                expires_at=expires_at,
                username=username,
            )
            
            if email_sent:
                # 邮件发送成功，提交用户创建和 waitlist 更新
                waitlist_entry.invited = True
                waitlist_entry.invited_at = beijing_now()
                waitlist_entry.sent_content = {
                    "username": username,
                    "expires_at": expires_at.isoformat(),
                    "sent_at": beijing_now().isoformat(),
                    "sent_by": current_user.id,
                }
                await db.commit()
                success_count += 1
                
                logger.info(
                    "admin_batch_send_invite_success",
                    admin_id=current_user.id,
                    email=email,
                    username=username,
                    user_id=new_user.id,
                )
            else:
                # 邮件发送失败，回滚用户创建
                logger.warning(
                    "admin_batch_send_invite_email_failed",
                    admin_id=current_user.id,
                    email=email,
                    username=username,
                )
                errors.append({
                    "email": email,
                    "error": "Failed to send email, user account not created"
                })
                failed_count += 1
                await db.rollback()
                
        except Exception as e:
            logger.error(
                "admin_batch_send_invite_error",
                admin_id=current_user.id,
                email=email,
                error=str(e),
            )
            errors.append({
                "email": email,
                "error": str(e)
            })
            failed_count += 1
            await db.rollback()
    
    logger.info(
        "admin_batch_send_invites_completed",
        admin_id=current_user.id,
        success=success_count,
        failed=failed_count,
    )
    
    return BatchSendInviteResponse(
        success=success_count,
        failed=failed_count,
        errors=errors,
    )


@router.post("/create-superuser")
async def create_initial_superuser(
    email: EmailStr,
    password: str,
    db: AsyncSession = Depends(get_db),
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    创建初始超级管理员（仅在没有超级管理员时可用）
    
    这是一个初始化端点，只有当系统中没有超级管理员时才能调用。
    创建第一个超级管理员后，此端点将返回错误。
    
    Args:
        email: 管理员邮箱
        password: 管理员密码
        
    Returns:
        创建结果
    """
    # 检查是否已存在超级管理员
    existing_superuser = await db.execute(
        select(User).where(User.is_superuser == True)
    )
    if existing_superuser.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Superuser already exists. This endpoint is disabled."
        )
    
    # 创建超级管理员
    username = email.split('@')[0]
    user_create = UserCreate(
        email=email.lower().strip(),
        username=username,
        password=password,
    )
    
    try:
        new_user = await user_manager.create(user_create)
        
        # 设置为超级管理员
        new_user.is_superuser = True
        new_user.is_verified = True
        new_user.is_active = True
        await db.commit()
        
        logger.info(
            "initial_superuser_created",
            user_id=new_user.id,
            email=email,
        )
        
        return {
            "success": True,
            "message": "Superuser created successfully",
            "email": email,
            "user_id": new_user.id,
        }
        
    except Exception as e:
        logger.error(
            "create_superuser_failed",
            email=email,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create superuser: {str(e)}"
        )

