"""
教程相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

from app.models.domain import LearningPreferences

# ===== 请求模型 =====

class TutorialRetryRequest(BaseModel):
    """教程重试请求"""
    preferences: LearningPreferences = Field(..., description="学习偏好")
    retry_reason: Optional[str] = Field(None, description="重试原因")
    
    model_config = {"json_schema_extra": {
        "example": {
            "preferences": {
                "learning_style": "visual",
                "depth_level": "intermediate"
            },
            "retry_reason": "内容太浅，需要更深入的讲解"
        }
    }}

class TutorialCreate(BaseModel):
    """教程创建Schema"""
    tutorial_id: str = Field(..., description="教程ID")
    concept_id: str = Field(..., description="关联的概念ID")
    content: dict = Field(..., description="教程内容（JSON格式）")
    version: int = Field(default=1, description="版本号")

class TutorialUpdate(BaseModel):
    """教程更新Schema"""
    content: Optional[dict] = Field(None, description="教程内容")
    version: Optional[int] = Field(None, description="版本号")

# ===== 响应模型 =====

class TutorialRetryResponse(BaseModel):
    """教程重试响应"""
    success: bool = Field(..., description="是否成功")
    tutorial_id: str = Field(..., description="教程ID")
    message: str = Field(..., description="提示消息")
    data: Optional[dict] = Field(None, description="生成结果")

class TutorialDetail(BaseModel):
    """教程详情"""
    tutorial_id: str
    concept_id: str
    content: dict
    version: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

