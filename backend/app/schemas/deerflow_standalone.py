"""
Deer-Flow 独立实验室 API Schema（无路线图学习上下文）
"""
from pydantic import BaseModel, Field

from app.schemas.mentor_deerflow import DeerFlowReasoningEffort, DeerFlowRuntimeMode


class DeerFlowStandaloneChatContext(BaseModel):
    """
    独立 Deer-Flow 聊天运行时上下文（与伴学共用 mode / reasoning_effort 语义）。
    """

    mode: DeerFlowRuntimeMode | None = Field(None, description="Deer-Flow 运行模式")
    reasoning_effort: DeerFlowReasoningEffort | None = Field(None, description="推理深度")


class DeerFlowStandaloneChatRequest(BaseModel):
    """
    独立 Deer-Flow 聊天请求。
    """

    message: str = Field(..., min_length=1, max_length=4000, description="用户当前输入")
    thread_id: str | None = Field(None, description="Deer-Flow 线程 ID")
    assistant_id: str | None = Field(None, description="Deer-Flow assistant ID")
    model_id: str | None = Field(None, description="模型注册表 ID")
    context: DeerFlowStandaloneChatContext = Field(..., description="运行时上下文")


class DeerFlowStandaloneThreadCreateRequest(BaseModel):
    """
    独立 Deer-Flow 线程创建请求。
    """

    title: str | None = Field(None, max_length=200, description="线程标题")
    assistant_id: str | None = Field(None, description="Deer-Flow assistant ID")
    model_id: str | None = Field(None, description="模型注册表 ID")
