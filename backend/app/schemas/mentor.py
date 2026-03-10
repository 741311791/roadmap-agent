"""
Mentor 聊天相关 Schema。
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


MentorAgentMode = Literal["companion", "tutoring"]
MentorMessageRole = Literal["user", "assistant"]
MentorHistoryMessageRole = Literal["user", "assistant", "system"]
MentorModelName = Literal["qwen-plus", "qwen-max"]  # pragma: allowlist secret


class MentorMessageInput(BaseModel):
    """
    Mentor 单条消息输入模型。

    Args:
        role: 消息角色（user 或 assistant）。
        content: 消息文本内容。

    Returns:
        无。

    Raises:
        ValidationError: 当字段类型不合法时抛出。
    """

    role: MentorMessageRole = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, description="消息内容")


class MentorChatRequest(BaseModel):
    """
    Mentor 流式聊天请求模型。

    Args:
        messages: 新消息列表（兼容旧版，后端仅消费最后一条 user 消息）。
        agent_mode: Agent 模式（companion/tutoring）。
        model_name: 模型名称（qwen 系列）。
        concept_id: 当前概念 ID（可选）。
        session_id: 会话 ID（可选，不传则自动创建）。

    Returns:
        无。

    Raises:
        ValidationError: 当字段不满足约束时抛出。
    """

    messages: list[MentorMessageInput] = Field(default_factory=list, description="新消息列表")
    agent_mode: MentorAgentMode = Field(..., description="Agent 模式")
    model_name: MentorModelName = Field(default="qwen-plus", description="模型名称")  # pragma: allowlist secret
    concept_id: str | None = Field(default=None, description="当前概念 ID")
    session_id: str | None = Field(default=None, description="会话 ID")


class MentorSessionSummaryResponse(BaseModel):
    """
    Mentor 会话摘要响应模型。

    Args:
        session_id: 会话 ID。
        roadmap_id: 路线图 ID。
        concept_id: 当前概念 ID。
        agent_mode: 会话模式。
        model_name: 模型名称。
        title: 会话标题。
        message_count: 消息数量。
        last_message_preview: 最后一条消息预览。
        updated_at: 更新时间。
    """

    session_id: str = Field(..., description="会话 ID")
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str | None = Field(default=None, description="当前概念 ID")
    agent_mode: MentorAgentMode = Field(..., description="会话模式")
    model_name: MentorModelName = Field(default="qwen-plus", description="模型名称")  # pragma: allowlist secret
    title: str | None = Field(default=None, description="会话标题")
    message_count: int = Field(default=0, description="消息数量")
    last_message_preview: str | None = Field(default=None, description="最后一条消息预览")
    updated_at: datetime = Field(..., description="更新时间")


class MentorHistoryMessageResponse(BaseModel):
    """
    Mentor 历史消息响应模型。

    Args:
        message_id: 消息 ID。
        role: 消息角色。
        content: 消息内容。
        message_metadata: 额外元数据。
        created_at: 创建时间。
    """

    message_id: str = Field(..., description="消息 ID")
    role: MentorHistoryMessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    message_metadata: dict[str, Any] | None = Field(default=None, description="额外元数据")
    created_at: datetime = Field(..., description="创建时间")


class MentorSSEEvent(BaseModel):
    """
    Mentor SSE 事件通用模型。

    Args:
        type: 事件类型。
        payload: 事件载荷。

    Returns:
        无。

    Raises:
        ValidationError: 当字段类型不合法时抛出。
    """

    type: str = Field(..., description="事件类型")
    payload: dict[str, Any] = Field(default_factory=dict, description="事件载荷")

