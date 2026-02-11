"""
管理员 API Schema

所有管理员相关的请求/响应模型，包括：
- 用户邀请
- Waitlist 管理
- Tavily API Key 管理
- 超级管理员管理
"""
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ============================================================
# 用户邀请相关
# ============================================================

class InviteUserRequest(BaseModel):
    """邀请用户请求"""
    email: EmailStr
    password_validity_days: int = 30
    send_email: bool = True


class InviteUserResponse(BaseModel):
    """邀请用户响应"""
    success: bool
    email: str
    username: str
    temp_password: str
    expires_at: str
    message: str


# ============================================================
# Waitlist 管理相关
# ============================================================

class WaitlistUserInfo(BaseModel):
    """Waitlist用户信息"""
    email: str
    source: str
    invited: bool
    invited_at: Optional[str] = None
    created_at: str


class WaitlistResponse(BaseModel):
    """Waitlist列表响应"""
    users: List[WaitlistUserInfo]
    total: int
    pending: int
    invited: int


class WaitlistInviteItem(BaseModel):
    """Waitlist邀请列表项（含凭证）"""
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
    """Waitlist邀请列表响应"""
    items: List[WaitlistInviteItem]
    total: int
    pending: int
    invited: int


class BatchSendInviteRequest(BaseModel):
    """批量发送邀请请求"""
    emails: List[str]
    password_validity_days: int = 30


class BatchSendInviteResponse(BaseModel):
    """批量发送响应"""
    success: int
    failed: int
    errors: List[dict]


# ============================================================
# Tavily API Key 管理相关
# ============================================================

class TavilyAPIKeyInfo(BaseModel):
    """Tavily API Key信息"""
    api_key: str
    plan_limit: int
    remaining_quota: int
    created_at: str
    updated_at: str


class TavilyAPIKeyListResponse(BaseModel):
    """Tavily API Key列表响应"""
    keys: List[TavilyAPIKeyInfo]
    total: int


class AddTavilyAPIKeyRequest(BaseModel):
    """添加Tavily API Key请求"""
    api_key: str
    plan_limit: int = 1000


class BatchAddTavilyKeysRequest(BaseModel):
    """批量添加Tavily API Keys请求"""
    keys: List[AddTavilyAPIKeyRequest]


class BatchAddTavilyKeysResponse(BaseModel):
    """批量添加Tavily API Keys响应"""
    success: int
    failed: int
    errors: List[dict]


class UpdateTavilyAPIKeyRequest(BaseModel):
    """更新Tavily API Key配额请求"""
    remaining_quota: Optional[int] = None
    plan_limit: Optional[int] = None


class BatchUpdateTavilyKeysRequest(BaseModel):
    """批量更新Tavily API Keys请求（通过官方API查询配额）"""
    api_keys: List[str] = Field(description="待更新的API Key列表")


class BatchUpdateTavilyKeysResponse(BaseModel):
    """批量更新Tavily API Keys响应"""
    success: int
    failed: int
    errors: List[dict]


class BatchDeleteTavilyKeysRequest(BaseModel):
    """批量删除Tavily API Keys请求"""
    api_keys: List[str] = Field(description="待删除的API Key列表")


class BatchDeleteTavilyKeysResponse(BaseModel):
    """批量删除Tavily API Keys响应"""
    success: int
    failed: int
    errors: List[dict]


class DeleteTavilyAPIKeyResponse(BaseModel):
    """删除Tavily API Key响应"""
    success: bool
    message: str


# ============================================================
# 超级管理员相关
# ============================================================

class CreateSuperuserRequest(BaseModel):
    """创建超级管理员请求"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="密码（至少8位）")


class CreateSuperuserResponse(BaseModel):
    """创建超级管理员响应"""
    success: bool
    user_id: str
    email: str
    message: str

