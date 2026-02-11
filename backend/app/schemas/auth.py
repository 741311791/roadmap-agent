"""
认证扩展 API Schema

包含登出、黑名单统计等
"""
from pydantic import BaseModel
from typing import List, Optional


# ============================================================
# 登出相关
# ============================================================

class LogoutResponse(BaseModel):
    """登出响应"""
    message: str
    user_id: str
    devices_count: Optional[int] = None  # 登出的设备数量（登出所有设备时返回）


# ============================================================
# 黑名单统计相关
# ============================================================

class BlacklistStatsResponse(BaseModel):
    """黑名单统计响应"""
    total_tokens: int
    active_tokens: int  # 活跃的token数量（未过期）
    expired_tokens: int  # 已过期的token数量

