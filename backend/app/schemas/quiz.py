"""
测验相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime

from app.models.domain import LearningPreferences

# ===== 请求模型 =====

class QuizRetryRequest(BaseModel):
    """测验重试请求"""
    preferences: LearningPreferences = Field(..., description="学习偏好")
    retry_reason: Optional[str] = Field(None, description="重试原因")

class QuizCreate(BaseModel):
    """测验创建Schema"""
    quiz_id: str = Field(..., description="测验ID")
    concept_id: str = Field(..., description="关联的概念ID")
    questions: list[dict] = Field(..., description="问题列表")
    version: int = Field(default=1, description="版本号")

class QuizUpdate(BaseModel):
    """测验更新Schema"""
    questions: Optional[list[dict]] = Field(None, description="问题列表")
    version: Optional[int] = Field(None, description="版本号")

class QuizSubmitRequest(BaseModel):
    """测验提交请求"""
    quiz_id: str = Field(..., description="测验ID")
    answers: dict = Field(..., description="用户答案")

# ===== 响应模型 =====

class QuizRetryResponse(BaseModel):
    """测验重试响应"""
    success: bool = Field(..., description="是否成功")
    quiz_id: str = Field(..., description="测验ID")
    message: str = Field(..., description="提示消息")
    data: Optional[dict] = Field(None, description="生成结果")

class QuizDetail(BaseModel):
    """测验详情"""
    quiz_id: str
    concept_id: str
    questions: list[dict]
    version: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class QuizSubmitResponse(BaseModel):
    """测验提交响应"""
    success: bool = Field(..., description="是否成功")
    score: int = Field(..., description="分数")
    total: int = Field(..., description="总分")
    feedback: dict = Field(..., description="反馈详情")

