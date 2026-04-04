"""
Mentor 运行时事件与输入模型
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


MentorAgentKind = Literal["qa", "guide", "quiz"]
MentorQaStyle = Literal["casual", "serious"]


class MentorEmotionAnalysis(BaseModel):
    """
    用户情绪分析结果
    """

    label: str = Field(..., description="情绪标签")
    summary: str = Field(..., description="情绪摘要")


class MentorQaAgentInput(BaseModel):
    """
    答疑 Agent 输入
    """

    user_message: str = Field(..., description="用户当前输入")
    history_messages: list[dict[str, str]] = Field(default_factory=list, description="短期上下文消息")
    concept_title: str | None = Field(None, description="当前概念标题")
    tutorial_excerpt: str | None = Field(None, description="当前教程摘要")
    roadmap_context: str | None = Field(None, description="路线图上下文摘要")
    ltm_facts: list[str] = Field(default_factory=list, description="长期记忆事实列表")
    ltm_preferences: list[str] = Field(default_factory=list, description="学习偏好记忆")
    ltm_goals: list[str] = Field(default_factory=list, description="学习目标记忆")
    ltm_misconceptions: list[str] = Field(default_factory=list, description="历史误区记忆")
    ltm_progress: list[str] = Field(default_factory=list, description="当前进展记忆")
    ltm_other_facts: list[str] = Field(default_factory=list, description="其他长期记忆")
    learning_profile: str | None = Field(None, description="学习画像摘要")
    qa_style: MentorQaStyle = Field(default="casual", description="答疑风格")
    emotion: MentorEmotionAnalysis = Field(..., description="当前用户情绪分析")
    trace_id: str | None = Field(None, description="业务链路追踪 ID")
    langfuse_trace_id: str | None = Field(None, description="Langfuse Trace ID")


class MentorPlaceholderAgentInput(BaseModel):
    """
    占位 Agent 输入
    """

    user_message: str = Field(..., description="用户当前输入")
    concept_title: str | None = Field(None, description="当前概念标题")
    agent_kind: MentorAgentKind = Field(..., description="占位 Agent 类型")


class MentorTextDeltaEvent(BaseModel):
    """
    Mentor 文本增量事件
    """

    type: Literal["text_delta"] = "text_delta"
    delta: str = Field(..., description="本次新增文本")


class MentorThinkingDeltaEvent(BaseModel):
    """
    Mentor 思考增量事件
    """

    type: Literal["thinking_delta"] = "thinking_delta"
    delta: str = Field(..., description="本次新增思考内容")


class MentorToolStartEvent(BaseModel):
    """
    Mentor 工具开始事件
    """

    type: Literal["tool_start"] = "tool_start"
    tool_call_id: str = Field(..., description="工具调用 ID")
    tool_name: str = Field(..., description="工具名称")
    arguments: dict[str, Any] = Field(default_factory=dict, description="工具输入参数")


class MentorToolResultEvent(BaseModel):
    """
    Mentor 工具结果事件
    """

    type: Literal["tool_result"] = "tool_result"
    tool_call_id: str = Field(..., description="工具调用 ID")
    tool_name: str = Field(..., description="工具名称")
    arguments: dict[str, Any] = Field(default_factory=dict, description="工具输入参数")
    result: str = Field(..., description="工具结果文本")
    is_error: bool = Field(default=False, description="是否为错误结果")


MentorStreamEvent = (
    MentorTextDeltaEvent
    | MentorThinkingDeltaEvent
    | MentorToolStartEvent
    | MentorToolResultEvent
)
