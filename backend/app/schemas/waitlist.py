"""
候补名单 API Schema

包含加入 Waitlist 的请求和响应模型
"""
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
    """
    success: bool
    message: str
    is_new: bool

