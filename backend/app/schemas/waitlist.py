"""
候补名单 API Schema

包含加入 Waitlist 和公开试用申请的请求与响应模型。
"""
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr


# ============================================================
# Waitlist 相关
# ============================================================

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
        position: 在候补名单中的位置（可选）
    """
    success: bool
    message: str
    is_new: bool
    position: Optional[int] = None  # 在候补名单中的位置


class TrialAccessRequest(BaseModel):
    """
    公开试用申请请求

    Args:
        email: 用户邮箱地址
        source: 来源标记（可选，默认为 landing_page）
    """

    email: EmailStr
    source: str = "landing_page"


class TrialAccessResponse(BaseModel):
    """
    公开试用申请响应

    Args:
        success: 是否成功
        email: 用户邮箱地址
        status: 当前申请状态
        message: 返回给前端展示的提示文案
    """

    success: bool
    email: str
    status: Literal["invited", "already_invited", "existing_account"]
    message: str

