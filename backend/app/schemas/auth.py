"""
认证扩展 API Schema

包含登出、黑名单统计等
"""
from pydantic import BaseModel
from typing import List


# ============================================================
# 登出相关
# ============================================================

class LogoutResponse(BaseModel):
    """登出响应"""
    message: str
    user_id: str


# ============================================================
# 黑名单统计相关
# ============================================================

class BlacklistStatsResponse(BaseModel):
    """黑名单统计响应"""
    total_tokens: int
    sample_tokens: List[dict]

