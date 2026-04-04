"""
Deer-Flow 伴学代理相关 Schema
"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DeerFlowThreadSource = Literal["deer_flow"]
DeerFlowMentorMessageRole = Literal["system", "user", "assistant"]
DeerFlowRuntimeMode = Literal["flash", "thinking", "pro", "ultra"]
DeerFlowReasoningEffort = Literal["minimal", "low", "medium", "high"]


class DeerFlowMentorWarmupRequest(BaseModel):
    """
    Deer-Flow 伴学上下文预热请求

    Args:
        roadmap_id: 路线图 ID
        concept_id: 当前概念 ID
        concept_title: 当前概念标题

    Returns:
        None

    Raises:
        None
    """

    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str | None = Field(None, description="当前概念 ID")
    concept_title: str | None = Field(None, description="当前概念标题")


class DeerFlowMentorChatContext(BaseModel):
    """
    Deer-Flow 聊天上下文

    Args:
        roadmap_id: 路线图 ID
        stage_id: 当前阶段 ID
        task_id: 当前任务 ID
        concept_id: 当前概念 ID
        concept_title: 当前概念标题
        tutorial_excerpt: 当前教程摘要
        roadmap_context: 当前路线图上下文摘要

    Returns:
        None

    Raises:
        None
    """

    roadmap_id: str = Field(..., description="路线图 ID")
    stage_id: str | None = Field(None, description="当前阶段 ID")
    task_id: str | None = Field(None, description="当前任务 ID")
    concept_id: str | None = Field(None, description="当前概念 ID")
    concept_title: str | None = Field(None, description="当前概念标题")
    tutorial_excerpt: str | None = Field(None, description="当前教程摘要")
    roadmap_context: str | None = Field(None, description="当前路线图上下文摘要")
    mode: DeerFlowRuntimeMode | None = Field(None, description="Deer-Flow 运行模式")
    reasoning_effort: DeerFlowReasoningEffort | None = Field(None, description="推理深度")


class DeerFlowMentorChatRequest(BaseModel):
    """
    Deer-Flow 伴学聊天请求

    Args:
        message: 用户当前输入
        thread_id: 线程 ID；为空时后端自动创建
        assistant_id: Deer-Flow assistant ID
        model_id: 模型注册表 ID
        context: 学习上下文

    Returns:
        None

    Raises:
        None
    """

    message: str = Field(..., min_length=1, max_length=4000, description="用户当前输入")
    thread_id: str | None = Field(None, description="Deer-Flow 线程 ID")
    assistant_id: str | None = Field(None, description="Deer-Flow assistant ID")
    model_id: str | None = Field(None, description="模型注册表 ID")
    context: DeerFlowMentorChatContext = Field(..., description="学习上下文")


class DeerFlowMentorThreadCreateRequest(BaseModel):
    """
    Deer-Flow 线程创建请求

    Args:
        roadmap_id: 路线图 ID
        stage_id: 当前阶段 ID
        task_id: 当前任务 ID
        concept_id: 当前概念 ID
        title: 线程标题
        assistant_id: Deer-Flow assistant ID
        model_id: 模型注册表 ID

    Returns:
        None

    Raises:
        None
    """

    roadmap_id: str = Field(..., description="路线图 ID")
    stage_id: str | None = Field(None, description="当前阶段 ID")
    task_id: str | None = Field(None, description="当前任务 ID")
    concept_id: str | None = Field(None, description="当前概念 ID")
    title: str | None = Field(None, max_length=200, description="线程标题")
    assistant_id: str | None = Field(None, description="Deer-Flow assistant ID")
    model_id: str | None = Field(None, description="模型注册表 ID")


class DeerFlowMentorThreadResponse(BaseModel):
    """
    Deer-Flow 线程响应

    Args:
        thread_id: 线程 ID
        user_id: 用户 ID
        roadmap_id: 路线图 ID
        stage_id: 当前阶段 ID
        task_id: 当前任务 ID
        concept_id: 当前概念 ID
        title: 线程标题
        source: 线程来源
        assistant_id: Deer-Flow assistant ID
        model_id: 模型注册表 ID
        status: 线程状态
        message_count: 消息数量
        last_message_preview: 最后一条消息预览
        last_message_at: 最后消息时间
        metadata: 扩展元数据
        created_at: 创建时间
        updated_at: 更新时间

    Returns:
        None

    Raises:
        None
    """

    thread_id: str = Field(..., description="线程 ID")
    user_id: str = Field(..., description="用户 ID")
    roadmap_id: str | None = Field(None, description="路线图 ID；空表示独立 DeerFlow 线程")
    stage_id: str | None = Field(None, description="当前阶段 ID")
    task_id: str | None = Field(None, description="当前任务 ID")
    concept_id: str | None = Field(None, description="当前概念 ID")
    title: str | None = Field(None, description="线程标题")
    source: DeerFlowThreadSource = Field(default="deer_flow", description="线程来源")
    assistant_id: str | None = Field(None, description="Deer-Flow assistant ID")
    model_id: str | None = Field(None, description="模型注册表 ID")
    status: str = Field(default="idle", description="线程状态")
    message_count: int = Field(default=0, description="消息数量")
    last_message_preview: str | None = Field(None, description="最后一条消息预览")
    last_message_at: datetime | None = Field(None, description="最后消息时间")
    metadata: dict[str, Any] = Field(default_factory=dict, description="扩展元数据")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class DeerFlowMentorThreadListResponse(BaseModel):
    """
    Deer-Flow 线程列表响应

    Args:
        items: 线程列表
        total: 总数

    Returns:
        None

    Raises:
        None
    """

    items: list[DeerFlowMentorThreadResponse] = Field(default_factory=list, description="线程列表")
    total: int = Field(..., description="总数")


class DeerFlowMentorMessageResponse(BaseModel):
    """
    Deer-Flow 消息响应

    Args:
        message_id: 消息 ID
        thread_id: 线程 ID
        role: 消息角色
        content: 消息内容
        message_metadata: 扩展元数据
        created_at: 创建时间

    Returns:
        None

    Raises:
        None
    """

    message_id: str = Field(..., description="消息 ID")
    thread_id: str = Field(..., description="线程 ID")
    role: DeerFlowMentorMessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    message_metadata: dict[str, Any] | None = Field(None, description="消息扩展元数据")
    created_at: datetime = Field(..., description="创建时间")


class DeerFlowMentorMessageListResponse(BaseModel):
    """
    Deer-Flow 消息列表响应

    Args:
        items: 消息列表
        total: 总数

    Returns:
        None

    Raises:
        None
    """

    items: list[DeerFlowMentorMessageResponse] = Field(default_factory=list, description="消息列表")
    total: int = Field(..., description="总数")
