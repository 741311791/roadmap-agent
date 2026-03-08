"""
Mentor 聊天相关 Schema。
"""
from typing import Any, Literal

from pydantic import BaseModel, Field


MentorAgentMode = Literal["companion", "tutoring"]
MentorMessageRole = Literal["user", "assistant"]


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
        messages: 历史消息列表。
        agent_mode: Agent 模式（companion/tutoring）。
        concept_id: 当前概念 ID（可选）。
        session_id: 会话 ID（可选，当前阶段仅用于追踪）。

    Returns:
        无。

    Raises:
        ValidationError: 当字段不满足约束时抛出。
    """

    messages: list[MentorMessageInput] = Field(default_factory=list, description="历史消息列表")
    agent_mode: MentorAgentMode = Field(..., description="Agent 模式")
    concept_id: str | None = Field(default=None, description="当前概念 ID")
    session_id: str | None = Field(default=None, description="会话 ID")


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

