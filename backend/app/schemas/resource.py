"""
资源推荐相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

from app.models.domain import LearningPreferences

# ===== 请求模型 =====

class ResourceRetryRequest(BaseModel):
    """资源推荐重试请求"""
    preferences: LearningPreferences = Field(..., description="学习偏好")
    retry_reason: Optional[str] = Field(None, description="重试原因")

class ResourceCreate(BaseModel):
    """资源创建Schema"""
    resource_id: str = Field(..., description="资源ID")
    concept_id: str = Field(..., description="关联的概念ID")
    resources: list[dict] = Field(..., description="资源列表")
    version: int = Field(default=1, description="版本号")

class ResourceUpdate(BaseModel):
    """资源更新Schema"""
    resources: Optional[list[dict]] = Field(None, description="资源列表")
    version: Optional[int] = Field(None, description="版本号")

# ===== 响应模型 =====

class ResourceRetryResponse(BaseModel):
    """资源推荐重试响应"""
    success: bool = Field(..., description="是否成功")
    resource_id: str = Field(..., description="资源ID")
    message: str = Field(..., description="提示消息")
    data: Optional[dict] = Field(None, description="生成结果")

class ResourceDetail(BaseModel):
    """资源详情"""
    resource_id: str
    concept_id: str
    resources: list[dict]
    version: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

