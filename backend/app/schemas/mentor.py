"""
AI 伴学助手相关 Schema
"""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MentorAgentType = Literal["tutoring", "company"]
MentorMessageRole = Literal["system", "user", "assistant"]
MentorMemoryJobStatus = Literal["pending", "processing", "succeeded", "failed", "dead_letter"]


class MentorWarmupRequest(BaseModel):
    """
    AI 伴学助手缓存预热请求

    Args:
        roadmap_id: 路线图 ID
        concept_id: 当前概念 ID（为 None 时预热路线图级别缓存）
        concept_title: 当前概念标题（用作 LTM 向量预查询词）
    """
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str | None = Field(None, description="当前概念 ID")
    concept_title: str | None = Field(None, description="当前概念标题，用于 LTM 预查询")


class MentorChatContext(BaseModel):
    """
    AI 伴学助手对话上下文

    Args:
        roadmap_id: 路线图 ID
        concept_id: 当前概念 ID
        concept_title: 当前概念标题
        tutorial_excerpt: 当前教程摘要
        roadmap_context: 当前路线图上下文摘要
    """
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str | None = Field(None, description="当前概念 ID")
    concept_title: str | None = Field(None, description="当前概念标题")
    tutorial_excerpt: str | None = Field(None, description="当前教程摘要")
    roadmap_context: str | None = Field(None, description="当前路线图上下文摘要")


class MentorChatRequest(BaseModel):
    """
    AI 伴学助手聊天请求

    Args:
        message: 用户当前输入
        session_id: 会话 ID；为空时由后端自动创建
        agent_type: AI 伴学助手模式
        model_id: 模型 ID；为空时使用系统默认配置
        context: 学习上下文
    """
    message: str = Field(..., min_length=1, max_length=4000, description="用户当前输入")
    session_id: str | None = Field(None, description="会话 ID")
    agent_type: MentorAgentType = Field(default="tutoring", description="AI 伴学助手模式")
    model_id: str | None = Field(None, description="指定模型 ID")
    context: MentorChatContext = Field(..., description="学习上下文")


class MentorChatMessageResponse(BaseModel):
    """
    AI 伴学助手消息响应

    Args:
        message_id: 消息 ID
        session_id: 会话 ID
        role: 消息角色
        content: 消息内容
        agent_type: 伴学模式
        model_id: 模型 ID
        trace_id: 链路追踪 ID
        created_at: 创建时间
    """
    message_id: str = Field(..., description="消息 ID")
    session_id: str = Field(..., description="会话 ID")
    role: MentorMessageRole = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")
    agent_type: MentorAgentType | None = Field(None, description="AI 伴学助手模式")
    model_id: str | None = Field(None, description="模型 ID")
    trace_id: str | None = Field(None, description="链路追踪 ID")
    created_at: datetime = Field(..., description="创建时间")


class MentorSessionResponse(BaseModel):
    """
    AI 伴学助手会话响应

    Args:
        session_id: 会话 ID
        user_id: 用户 ID
        roadmap_id: 路线图 ID
        concept_id: 当前概念 ID
        title: 会话标题
        agent_type: 伴学模式
        model_id: 最近使用模型
        message_count: 消息数量
        last_message_preview: 最后一条消息预览
        created_at: 创建时间
        updated_at: 更新时间
    """
    session_id: str = Field(..., description="会话 ID")
    user_id: str = Field(..., description="用户 ID")
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str | None = Field(None, description="当前概念 ID")
    title: str | None = Field(None, description="会话标题")
    agent_type: MentorAgentType = Field(..., description="AI 伴学助手模式")
    model_id: str | None = Field(None, description="最近使用模型")
    message_count: int = Field(..., description="消息数量")
    last_message_preview: str | None = Field(None, description="最后一条消息预览")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class MentorSessionCreateRequest(BaseModel):
    """
    AI 伴学助手会话创建请求

    Args:
        roadmap_id: 路线图 ID
        concept_id: 当前概念 ID
        title: 会话标题
        agent_type: AI 伴学助手模式
        model_id: 默认模型 ID
    """
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str | None = Field(None, description="当前概念 ID")
    title: str | None = Field(None, max_length=200, description="会话标题")
    agent_type: MentorAgentType = Field(default="tutoring", description="AI 伴学助手模式")
    model_id: str | None = Field(None, description="默认模型 ID")


class MentorSessionListResponse(BaseModel):
    """
    AI 伴学助手会话列表响应

    Args:
        items: 会话列表
        total: 总数
    """
    items: list[MentorSessionResponse] = Field(default_factory=list, description="会话列表")
    total: int = Field(..., description="总数")


class MentorMessageListResponse(BaseModel):
    """
    AI 伴学助手消息列表响应

    Args:
        items: 消息列表
        total: 总数
    """
    items: list[MentorChatMessageResponse] = Field(default_factory=list, description="消息列表")
    total: int = Field(..., description="总数")


class MentorMemoryJobResponse(BaseModel):
    """
    AI 伴学助手记忆任务响应

    Args:
        job_id: 任务 ID
        message_id: 消息 ID
        session_id: 会话 ID
        user_id: 用户 ID
        celery_task_id: Celery 任务 ID
        status: 任务状态
        retry_count: 重试次数
        last_error: 最近错误
        started_at: 开始时间
        finished_at: 结束时间
        created_at: 创建时间
        updated_at: 更新时间
    """
    job_id: str = Field(..., description="任务 ID")
    message_id: str = Field(..., description="消息 ID")
    session_id: str = Field(..., description="会话 ID")
    user_id: str = Field(..., description="用户 ID")
    celery_task_id: str | None = Field(None, description="Celery 任务 ID")
    status: MentorMemoryJobStatus = Field(..., description="任务状态")
    retry_count: int = Field(..., description="重试次数")
    last_error: str | None = Field(None, description="最近错误")
    started_at: datetime | None = Field(None, description="开始时间")
    finished_at: datetime | None = Field(None, description="结束时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class LearningNoteCreate(BaseModel):
    """
    学习笔记创建请求

    Args:
        roadmap_id: 路线图 ID
        concept_id: 概念 ID
        title: 笔记标题
        content: 笔记内容
        source: 来源
        tags: 标签列表
    """
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str = Field(..., description="概念 ID")
    title: str | None = Field(None, max_length=200, description="笔记标题")
    content: str = Field(..., min_length=1, description="笔记内容")
    source: Literal["manual", "ai_generated", "chat_extracted"] = Field(
        default="manual",
        description="笔记来源"
    )
    tags: list[str] = Field(default_factory=list, description="标签列表")


class LearningNoteUpdate(BaseModel):
    """
    学习笔记更新请求

    Args:
        title: 笔记标题
        content: 笔记内容
        tags: 标签列表
    """
    title: str | None = Field(None, max_length=200, description="笔记标题")
    content: str | None = Field(None, min_length=1, description="笔记内容")
    tags: list[str] | None = Field(None, description="标签列表")
