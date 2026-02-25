"""
路线图生成 API Schema

包含路线图生成、内容重试、任务取消等
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal
from app.models.domain import LearningPreferences


# ============================================================
# 路线图生成相关
# ============================================================

class GenerateRoadmapResponse(BaseModel):
    """路线图生成响应"""
    task_id: str = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态（pending/processing/completed/failed）")
    message: str = Field(..., description="响应消息")


# ============================================================
# 内容重试相关
# ============================================================

class RetryContentRequest(BaseModel):
    """内容重新生成请求（来自前端的 API 层 Schema）

    preferences 为可选字段：前端不传时由后端从路线图 framework_data 自动提取。
    """
    preferences: Optional[LearningPreferences] = Field(None, description="学习偏好（缺省时自动从路线图数据中提取）")
    retry_reason: Optional[str] = Field(None, description="重新生成原因")


class RetryContentResponse(BaseModel):
    """内容重试响应"""
    success: bool
    concept_id: str
    content_type: Literal["tutorial", "resources", "quiz"]
    message: str
    data: Optional[dict] = None


# ============================================================
# 任务取消相关
# ============================================================

class CancelTaskResponse(BaseModel):
    """任务取消响应"""
    success: bool
    task_id: str
    message: str
    previous_status: Optional[str] = None


# ============================================================
# 任务删除相关
# ============================================================

class DeleteTaskResponse(BaseModel):
    """任务删除响应"""
    success: bool
    task_id: str
    message: str
    previous_status: Optional[str] = None

