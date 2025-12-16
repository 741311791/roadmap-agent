"""
候补名单 API 端点

提供 Join Waitlist 功能的后端支持。
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import structlog

from app.db.session import get_db
from app.models.database import WaitlistEmail, beijing_now

router = APIRouter(prefix="/waitlist", tags=["waitlist"])
logger = structlog.get_logger()


class WaitlistJoinRequest(BaseModel):
    """
    加入候补名单请求
    
    Args:
        email: 用户邮箱地址
        source: 来源标记（可选，默认为 landing_page）
    """
    email: EmailStr
    source: str = "landing_page"


class WaitlistJoinResponse(BaseModel):
    """
    加入候补名单响应
    
    Args:
        success: 是否成功
        message: 提示消息
        is_new: 是否为新用户（首次加入）
    """
    success: bool
    message: str
    is_new: bool


@router.post("", response_model=WaitlistJoinResponse)
async def join_waitlist(
    request: WaitlistJoinRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    加入候补名单
    
    用户在首页提交邮箱后调用此接口，将邮箱存入候补名单。
    如果邮箱已存在，返回成功但标记为非新用户。
    
    Args:
        request: 包含邮箱和来源的请求体
        db: 数据库会话
        
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
        logger.info(
            "waitlist_email_already_exists",
            email=email,
        )
        return WaitlistJoinResponse(
            success=True,
            message="You're already on our waitlist! We'll be in touch soon.",
            is_new=False,
        )
    
    # 创建新记录
    waitlist_entry = WaitlistEmail(
        email=email,
        source=request.source,
        invited=False,
        invited_at=None,
        created_at=beijing_now(),
    )
    
    db.add(waitlist_entry)
    await db.commit()
    
    logger.info(
        "waitlist_email_added",
        email=email,
        source=request.source,
    )
    
    return WaitlistJoinResponse(
        success=True,
        message="Thank you for joining our waitlist! We'll notify you when access is available.",
        is_new=True,
    )


@router.get("/count")
async def get_waitlist_count(
    db: AsyncSession = Depends(get_db),
):
    """
    获取候补名单人数（仅供管理员查看）
    
    Returns:
        候补名单统计信息
    """
    from sqlalchemy import func
    
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
    
    return {
        "total": total,
        "invited": invited,
        "pending": total - invited,
    }

