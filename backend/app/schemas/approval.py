"""
人工审核 API Schema

包含审核请求和响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional


# ============================================================
# 审核相关
# ============================================================

class ApprovalRequest(BaseModel):
    """审核请求模型"""
    approved: bool = Field(..., description="是否批准")
    feedback: Optional[str] = Field(None, description="反馈意见")


class ApprovalResponse(BaseModel):
    """审核响应模型"""
    status: str = Field(..., description="审核状态：approved/rejected")
    message: str = Field(..., description="状态消息")
    task_id: str = Field(..., description="任务ID")
    feedback: Optional[str] = Field(None, description="反馈意见")

