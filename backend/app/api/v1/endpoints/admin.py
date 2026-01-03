"""
管理员 API 端点

提供用户邀请、Waitlist 管理等管理功能。
"""
import secrets
import string
import time
import httpx
from datetime import timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, EmailStr
import structlog
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.db.session import get_db
from app.models.database import User, WaitlistEmail, TavilyAPIKey, beijing_now
from app.core.auth.deps import current_superuser
from app.core.auth.user_manager import get_user_manager, UserManager
from app.core.auth.schemas import UserCreate
from app.services.email_service import get_email_service, EmailService
from app.db.repositories.tavily_key_repo import TavilyKeyRepository

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


class TavilyAPIKeyInfo(BaseModel):
    """
    Tavily API Key 信息
    
    Args:
        api_key: API Key（脱敏显示）
        plan_limit: 计划总配额
        remaining_quota: 剩余配额
        created_at: 录入时间
        updated_at: 最后更新时间
    """
    api_key: str
    plan_limit: int
    remaining_quota: int
    created_at: str
    updated_at: str


class TavilyAPIKeyListResponse(BaseModel):
    """
    Tavily API Key 列表响应
    
    Args:
        keys: Key 列表
        total: 总数
    """
    keys: List[TavilyAPIKeyInfo]
    total: int


class AddTavilyAPIKeyRequest(BaseModel):
    """
    添加 Tavily API Key 请求
    
    Args:
        api_key: Tavily API Key
        plan_limit: 计划总配额（每月总请求数）
    """
    api_key: str
    plan_limit: int = 1000


class BatchAddTavilyKeysRequest(BaseModel):
    """
    批量添加 Tavily API Keys 请求
    
    Args:
        keys: Key 列表，每个Key包含 api_key 和 plan_limit
    """
    keys: List[AddTavilyAPIKeyRequest]


class BatchAddTavilyKeysResponse(BaseModel):
    """
    批量添加 Tavily API Keys 响应
    
    Args:
        success: 成功添加的数量
        failed: 失败的数量
        errors: 失败详情列表
    """
    success: int
    failed: int
    errors: List[dict]


class UpdateTavilyAPIKeyRequest(BaseModel):
    """
    更新 Tavily API Key 配额请求
    
    Args:
        remaining_quota: 剩余配额
        plan_limit: 计划总配额（可选）
    """
    remaining_quota: Optional[int] = None
    plan_limit: Optional[int] = None


class DeleteTavilyAPIKeyResponse(BaseModel):
    """
    删除 Tavily API Key 响应
    
    Args:
        success: 是否成功
        message: 提示消息
    """
    success: bool
    message: str


class RefreshQuotaResponse(BaseModel):
    """
    刷新配额响应
    
    Args:
        success: 成功更新的数量
        failed: 失败的数量
        total_keys: 总 Key 数量
        elapsed_seconds: 耗时（秒）
    """
    success: int
    failed: int
    total_keys: int
    elapsed_seconds: float


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
    
    采用"一次读取，批量处理，一次提交"策略优化性能。
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
    
    # 标准化邮箱列表
    normalized_emails = [email.lower().strip() for email in request.emails]
    
    # Step 1: 一次性批量读取所有 waitlist 记录
    waitlist_result = await db.execute(
        select(WaitlistEmail).where(WaitlistEmail.email.in_(normalized_emails))
    )
    waitlist_map = {entry.email: entry for entry in waitlist_result.scalars().all()}
    
    # Step 2: 一次性批量读取所有已存在用户
    existing_users_result = await db.execute(
        select(User.email).where(User.email.in_(normalized_emails))
    )
    existing_users_set = set(existing_users_result.scalars().all())
    
    # Step 3: 预处理，区分可处理和不可处理的邮箱
    errors = []
    emails_to_process = []
    
    for email in normalized_emails:
        waitlist_entry = waitlist_map.get(email)
        
        if not waitlist_entry:
            errors.append({"email": email, "error": "Email not found in waitlist"})
            continue
        
        if waitlist_entry.invited:
            errors.append({"email": email, "error": "Invitation already sent"})
            continue
        
        if email in existing_users_set:
            errors.append({"email": email, "error": "User account already exists"})
            continue
        
        emails_to_process.append((email, waitlist_entry))
    
    # Step 4: 处理可邀请的邮箱（邮件发送是外部副作用，需逐个处理）
    success_count = 0
    pending_commits = []  # 收集待提交的变更
    
    for email, waitlist_entry in emails_to_process:
        try:
            username = email.split('@')[0]
            temp_password = generate_random_password()
            expires_at = beijing_now() + timedelta(days=request.password_validity_days)
            
            # 创建用户账号
            user_create = UserCreate(
                email=email,
                username=username,
                password=temp_password,
            )
            new_user = await user_manager.create(user_create)
            new_user.password_expires_at = expires_at
            
            # 发送邀请邮件
            email_sent = await email_service.send_invite_email(
                to_email=email,
                temp_password=temp_password,
                expires_at=expires_at,
                username=username,
            )
            
            if email_sent:
                # 更新 waitlist 记录
                waitlist_entry.username = username
                waitlist_entry.password = temp_password
                waitlist_entry.expires_at = expires_at
                waitlist_entry.invited = True
                waitlist_entry.invited_at = beijing_now()
                waitlist_entry.sent_content = {
                    "username": username,
                    "expires_at": expires_at.isoformat(),
                    "sent_at": beijing_now().isoformat(),
                    "sent_by": current_user.id,
                }
                pending_commits.append((email, username, new_user.id))
                success_count += 1
                
                logger.info(
                    "admin_batch_send_invite_success",
                    admin_id=current_user.id,
                    email=email,
                    username=username,
                    user_id=new_user.id,
                )
            else:
                # 邮件发送失败，回滚此用户创建
                await db.rollback()
                errors.append({
                    "email": email,
                    "error": "Failed to send email, user account not created"
                })
                logger.warning(
                    "admin_batch_send_invite_email_failed",
                    admin_id=current_user.id,
                    email=email,
                )
                
        except Exception as e:
            await db.rollback()
            errors.append({"email": email, "error": str(e)})
            logger.error(
                "admin_batch_send_invite_error",
                admin_id=current_user.id,
                email=email,
                error=str(e),
            )
    
    # Step 5: 一次性提交所有成功的变更
    if pending_commits:
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(
                "admin_batch_send_invites_commit_failed",
                admin_id=current_user.id,
                error=str(e),
            )
            # 提交失败，所有待提交的都算失败
            for email, _, _ in pending_commits:
                errors.append({"email": email, "error": f"Final commit failed: {str(e)}"})
            success_count = 0
    
    logger.info(
        "admin_batch_send_invites_completed",
        admin_id=current_user.id,
        success=success_count,
        failed=len(errors),
    )
    
    return BatchSendInviteResponse(
        success=success_count,
        failed=len(errors),
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


# ============================================================
# Tavily API Key Management
# ============================================================

@router.get("/tavily-keys", response_model=TavilyAPIKeyListResponse)
async def get_tavily_keys(
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    获取所有 Tavily API Keys
    
    只有超级管理员可以查看。
    
    Returns:
        Tavily API Key 列表和统计信息
    """
    try:
        repo = TavilyKeyRepository(db)
        keys = await repo.get_all_keys()
        
        logger.info(
            "admin_get_tavily_keys",
            admin_id=current_user.id,
            total_keys=len(keys),
        )
        
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
        logger.error(
            "admin_get_tavily_keys_failed",
            admin_id=current_user.id,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get Tavily API Keys: {str(e)}"
        )


@router.post("/tavily-keys", response_model=TavilyAPIKeyInfo)
async def add_tavily_key(
    request: AddTavilyAPIKeyRequest,
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    添加单个 Tavily API Key
    
    只有超级管理员可以调用此接口。
    
    Args:
        request: 添加请求，包含 API Key 和计划配额
        
    Returns:
        添加的 Tavily API Key 信息
    """
    logger.info(
        "admin_add_tavily_key_requested",
        admin_id=current_user.id,
        key_prefix=request.api_key[:10] + "...",
        plan_limit=request.plan_limit,
    )
    
    try:
        # 检查 Key 是否已存在
        repo = TavilyKeyRepository(db)
        existing_key = await repo.get_by_key(request.api_key)
        
        if existing_key:
            raise HTTPException(
                status_code=400,
                detail=f"API Key already exists"
            )
        
        # 创建新的 Key 记录
        new_key = TavilyAPIKey(
            api_key=request.api_key,
            plan_limit=request.plan_limit,
            remaining_quota=request.plan_limit,  # 初始配额等于计划配额
        )
        
        db.add(new_key)
        await db.commit()
        await db.refresh(new_key)
        
        logger.info(
            "admin_add_tavily_key_success",
            admin_id=current_user.id,
            key_prefix=request.api_key[:10] + "...",
        )
        
        return TavilyAPIKeyInfo(
            api_key=f"{new_key.api_key[:10]}...{new_key.api_key[-4:]}" if len(new_key.api_key) > 14 else new_key.api_key,
            plan_limit=new_key.plan_limit,
            remaining_quota=new_key.remaining_quota,
            created_at=new_key.created_at.isoformat(),
            updated_at=new_key.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "admin_add_tavily_key_failed",
            admin_id=current_user.id,
            key_prefix=request.api_key[:10] + "...",
            error=str(e),
        )
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add Tavily API Key: {str(e)}"
        )


@router.post("/tavily-keys/batch", response_model=BatchAddTavilyKeysResponse)
async def batch_add_tavily_keys(
    request: BatchAddTavilyKeysRequest,
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    批量添加 Tavily API Keys
    
    采用"一次读取，批量处理，一次提交"策略优化性能。
    支持部分成功模式：成功的添加记录，失败的收集错误信息。
    只有超级管理员可以调用此接口。
    
    Args:
        request: 批量添加请求，包含 Key 列表
        
    Returns:
        批量添加结果，包含成功/失败数量和错误详情
    """
    logger.info(
        "admin_batch_add_tavily_keys_requested",
        admin_id=current_user.id,
        key_count=len(request.keys),
    )
    
    errors = []
    new_keys_to_add = []
    
    # Step 1: 一次性读取所有请求中的 Key，检查哪些已存在
    requested_api_keys = [key_req.api_key for key_req in request.keys]
    existing_result = await db.execute(
        select(TavilyAPIKey.api_key).where(TavilyAPIKey.api_key.in_(requested_api_keys))
    )
    existing_keys_set = set(existing_result.scalars().all())
    
    # Step 2: 批量处理，区分已存在和新增的 Key
    for key_req in request.keys:
        if key_req.api_key in existing_keys_set:
            errors.append({
                "api_key": f"{key_req.api_key[:10]}...",
                "error": "API Key already exists"
            })
        else:
            # 构建新 Key 对象（暂不提交）
            new_key = TavilyAPIKey(
                api_key=key_req.api_key,
                plan_limit=key_req.plan_limit,
                remaining_quota=key_req.plan_limit,
            )
            new_keys_to_add.append(new_key)
    
    # Step 3: 一次性批量添加所有新 Key
    success_count = 0
    if new_keys_to_add:
        try:
            db.add_all(new_keys_to_add)
            await db.commit()
            success_count = len(new_keys_to_add)
            
            logger.info(
                "admin_batch_add_tavily_keys_bulk_insert",
                admin_id=current_user.id,
                inserted_count=success_count,
            )
        except Exception as e:
            await db.rollback()
            logger.error(
                "admin_batch_add_tavily_keys_bulk_insert_failed",
                admin_id=current_user.id,
                error=str(e),
            )
            # 批量插入失败，所有待添加的 Key 都记录为失败
            for key_obj in new_keys_to_add:
                errors.append({
                    "api_key": f"{key_obj.api_key[:10]}...",
                    "error": f"Bulk insert failed: {str(e)}"
                })
    
    failed_count = len(errors)
    
    logger.info(
        "admin_batch_add_tavily_keys_completed",
        admin_id=current_user.id,
        success=success_count,
        failed=failed_count,
    )
    
    return BatchAddTavilyKeysResponse(
        success=success_count,
        failed=failed_count,
        errors=errors,
    )


@router.put("/tavily-keys/{api_key}", response_model=TavilyAPIKeyInfo)
async def update_tavily_key(
    api_key: str,
    request: UpdateTavilyAPIKeyRequest,
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    更新 Tavily API Key 配额
    
    只有超级管理员可以调用此接口。
    
    Args:
        api_key: API Key
        request: 更新请求，包含要更新的字段
        
    Returns:
        更新后的 Tavily API Key 信息
    """
    logger.info(
        "admin_update_tavily_key_requested",
        admin_id=current_user.id,
        key_prefix=api_key[:10] + "...",
    )
    
    try:
        repo = TavilyKeyRepository(db)
        key_record = await repo.get_by_key(api_key)
        
        if not key_record:
            raise HTTPException(
                status_code=404,
                detail="API Key not found"
            )
        
        # 更新字段
        if request.remaining_quota is not None:
            key_record.remaining_quota = request.remaining_quota
        
        if request.plan_limit is not None:
            key_record.plan_limit = request.plan_limit
        
        key_record.updated_at = beijing_now()
        
        await db.commit()
        await db.refresh(key_record)
        
        logger.info(
            "admin_update_tavily_key_success",
            admin_id=current_user.id,
            key_prefix=api_key[:10] + "...",
        )
        
        return TavilyAPIKeyInfo(
            api_key=f"{key_record.api_key[:10]}...{key_record.api_key[-4:]}" if len(key_record.api_key) > 14 else key_record.api_key,
            plan_limit=key_record.plan_limit,
            remaining_quota=key_record.remaining_quota,
            created_at=key_record.created_at.isoformat(),
            updated_at=key_record.updated_at.isoformat(),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "admin_update_tavily_key_failed",
            admin_id=current_user.id,
            key_prefix=api_key[:10] + "...",
            error=str(e),
        )
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update Tavily API Key: {str(e)}"
        )


@router.delete("/tavily-keys/{api_key}", response_model=DeleteTavilyAPIKeyResponse)
async def delete_tavily_key(
    api_key: str,
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    删除 Tavily API Key
    
    只有超级管理员可以调用此接口。
    
    Args:
        api_key: API Key
        
    Returns:
        删除结果
    """
    logger.info(
        "admin_delete_tavily_key_requested",
        admin_id=current_user.id,
        key_prefix=api_key[:10] + "...",
    )
    
    try:
        repo = TavilyKeyRepository(db)
        key_record = await repo.get_by_key(api_key)
        
        if not key_record:
            raise HTTPException(
                status_code=404,
                detail="API Key not found"
            )
        
        await db.delete(key_record)
        await db.commit()
        
        logger.info(
            "admin_delete_tavily_key_success",
            admin_id=current_user.id,
            key_prefix=api_key[:10] + "...",
        )
        
        return DeleteTavilyAPIKeyResponse(
            success=True,
            message="API Key deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "admin_delete_tavily_key_failed",
            admin_id=current_user.id,
            key_prefix=api_key[:10] + "...",
            error=str(e),
        )
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete Tavily API Key: {str(e)}"
        )


# ============================================================
# Tavily API Key Quota Refresh
# ============================================================

# 配置参数
TAVILY_USAGE_API_URL = "https://api.tavily.com/usage"
HTTP_TIMEOUT = 30.0
MAX_RETRIES = 3


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    reraise=True,
)
async def fetch_tavily_usage(api_key: str, client: httpx.AsyncClient) -> dict:
    """
    调用 Tavily 官方 API 查询配额使用情况（带重试）
    
    Args:
        api_key: Tavily API Key
        client: HTTP 客户端
        
    Returns:
        包含配额信息的字典
        
    Raises:
        httpx.HTTPError: HTTP 请求错误
        httpx.TimeoutException: 请求超时
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    response = await client.get(
        TAVILY_USAGE_API_URL,
        headers=headers,
        timeout=HTTP_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


async def update_single_key_quota(
    key_record: TavilyAPIKey,
    session: AsyncSession,
    client: httpx.AsyncClient
) -> bool:
    """
    更新单个 API Key 的配额信息
    
    Args:
        key_record: TavilyAPIKey 数据库记录
        session: 数据库会话
        client: HTTP 客户端
        
    Returns:
        更新是否成功
    """
    api_key = key_record.api_key
    key_prefix = api_key[:10] + "..." if len(api_key) > 10 else api_key
    old_quota = key_record.remaining_quota
    old_limit = key_record.plan_limit
    
    try:
        # 调用 Tavily API 获取使用量
        logger.debug(
            "fetching_tavily_usage",
            key_prefix=key_prefix,
            old_quota=old_quota
        )
        
        usage_data = await fetch_tavily_usage(api_key, client)
        
        # 解析响应数据
        account_data = usage_data.get("account", {})
        plan_usage = account_data.get("plan_usage", 0)
        plan_limit = account_data.get("plan_limit", 0)
        
        if plan_limit == 0:
            logger.warning(
                "tavily_plan_limit_zero",
                key_prefix=key_prefix,
                usage_data=usage_data
            )
            return False
        
        # 计算剩余配额
        remaining_quota = plan_limit - plan_usage
        
        # 更新数据库（仅在值发生变化时）
        if remaining_quota != old_quota or plan_limit != old_limit:
            key_record.remaining_quota = remaining_quota
            key_record.plan_limit = plan_limit
            # updated_at 会通过 onupdate 自动更新
            
            await session.commit()
            
            logger.info(
                "tavily_quota_updated",
                key_prefix=key_prefix,
                old_quota=old_quota,
                new_quota=remaining_quota,
                plan_limit=plan_limit,
                plan_usage=plan_usage,
                quota_change=remaining_quota - old_quota
            )
        else:
            logger.debug(
                "tavily_quota_unchanged",
                key_prefix=key_prefix,
                quota=remaining_quota,
                limit=plan_limit
            )
        
        return True
        
    except httpx.HTTPStatusError as e:
        logger.error(
            "tavily_api_http_error",
            key_prefix=key_prefix,
            status_code=e.response.status_code,
            error=str(e),
            response_text=e.response.text[:200] if e.response else None
        )
        await session.rollback()
        return False
        
    except httpx.TimeoutException as e:
        logger.error(
            "tavily_api_timeout",
            key_prefix=key_prefix,
            error=str(e),
            timeout=HTTP_TIMEOUT
        )
        await session.rollback()
        return False
        
    except Exception as e:
        logger.error(
            "tavily_quota_update_failed",
            key_prefix=key_prefix,
            error=str(e),
            error_type=type(e).__name__
        )
        await session.rollback()
        return False


@router.post("/tavily-keys/refresh-quota", response_model=RefreshQuotaResponse)
async def refresh_tavily_quota(
    current_user: User = Depends(current_superuser),
    db: AsyncSession = Depends(get_db),
):
    """
    手动刷新所有 Tavily API Keys 的配额信息
    
    调用 Tavily 官方 API 获取最新的配额使用情况并更新数据库。
    只有超级管理员可以调用此接口。
    
    Returns:
        刷新结果，包含成功/失败数量和耗时
    """
    start_time = time.time()
    
    logger.info(
        "admin_refresh_tavily_quota_requested",
        admin_id=current_user.id,
    )
    
    try:
        # 查询所有 Key
        stmt = select(TavilyAPIKey).where(
            TavilyAPIKey.remaining_quota <= TavilyAPIKey.plan_limit
        )
        result = await db.execute(stmt)
        keys = result.scalars().all()
        
        total_keys = len(keys)
        if total_keys == 0:
            logger.warning(
                "admin_refresh_tavily_quota_no_keys",
                admin_id=current_user.id,
            )
            return RefreshQuotaResponse(
                success=0,
                failed=0,
                total_keys=0,
                elapsed_seconds=0.0
            )
        
        logger.info(
            "admin_refresh_tavily_quota_keys_fetched",
            admin_id=current_user.id,
            total_keys=total_keys
        )
        
        # 创建 HTTP 客户端（复用连接）
        async with httpx.AsyncClient() as client:
            success_count = 0
            failed_count = 0
            
            # 逐个更新 Key
            for key_record in keys:
                success = await update_single_key_quota(key_record, db, client)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            
            elapsed_time = time.time() - start_time
            
            logger.info(
                "admin_refresh_tavily_quota_completed",
                admin_id=current_user.id,
                total_keys=total_keys,
                success_count=success_count,
                failed_count=failed_count,
                elapsed_seconds=round(elapsed_time, 2)
            )
            
            return RefreshQuotaResponse(
                success=success_count,
                failed=failed_count,
                total_keys=total_keys,
                elapsed_seconds=round(elapsed_time, 2)
            )
            
    except Exception as e:
        logger.error(
            "admin_refresh_tavily_quota_failed",
            admin_id=current_user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh Tavily quota: {str(e)}"
        )


