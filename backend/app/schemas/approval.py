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
    success: bool
    message: str
    task_id: str

