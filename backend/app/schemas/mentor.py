"""
伴学 Mentor 相关 Schema 定义

遵循企业级架构规范的 Pydantic 数据传输对象
"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict


# ============================================================
# 基础 Schema
# ============================================================

class ChatSessionBase(BaseModel):
    """聊天会话基础 Schema"""
    user_id: str = Field(..., description="用户ID")
    roadmap_id: str = Field(..., description="路线图ID")
    concept_id: Optional[str] = Field(None, description="关联概念ID")
    title: Optional[str] = Field(None, description="会话标题")


class ChatMessageBase(BaseModel):
    """聊天消息基础 Schema"""
    role: Literal["user", "assistant", "system"] = Field(..., description="消息角色")
    content: str = Field(..., min_length=1, max_length=10000, description="消息内容")


class LearningNoteBase(BaseModel):
    """学习笔记基础 Schema"""
    user_id: str = Field(..., description="用户ID")
    roadmap_id: str = Field(..., description="路线图ID")
    concept_id: str = Field(..., description="概念ID")
    content: str = Field(..., min_length=1, max_length=50000, description="笔记内容(Markdown)")


# ============================================================
# 请求 Schema (Create/Update)
# ============================================================

class ChatMessageCreate(ChatMessageBase):
    """创建聊天消息请求"""
    session_id: Optional[str] = Field(None, description="会话ID(新会话时为空)")
    intent_type: Optional[str] = Field(None, description="意图类型")
    message_metadata: Optional[dict] = Field(None, description="消息元数据")


class ChatStreamRequest(BaseModel):
    """流式聊天请求"""
    user_id: str = Field(..., description="用户ID")
    roadmap_id: str = Field(..., description="路线图ID")
    concept_id: Optional[str] = Field(None, description="概念ID")
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    session_id: Optional[str] = Field(None, description="会话ID(新会话时为空)")


class LearningNoteCreate(LearningNoteBase):
    """创建学习笔记请求"""
    title: Optional[str] = Field(None, max_length=200, description="笔记标题")
    source: Literal["manual", "ai_generated", "chat_extracted"] = Field(
        "manual", 
        description="笔记来源"
    )
    tags: List[str] = Field(default_factory=list, description="标签列表")


class LearningNoteUpdate(BaseModel):
    """更新学习笔记请求"""
    title: Optional[str] = Field(None, max_length=200, description="笔记标题")
    content: Optional[str] = Field(None, min_length=1, max_length=50000, description="笔记内容")
    tags: Optional[List[str]] = Field(None, description="标签列表")


# ============================================================
# 响应 Schema (Response)
# ============================================================

class ChatSessionResponse(ChatSessionBase):
    """聊天会话响应"""
    model_config = ConfigDict(from_attributes=True)
    
    session_id: str
    message_count: int = 0
    last_message_preview: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(ChatMessageBase):
    """聊天消息响应"""
    model_config = ConfigDict(from_attributes=True)
    
    message_id: str
    session_id: str
    intent_type: Optional[str] = None
    created_at: datetime


class LearningNoteResponse(LearningNoteBase):
    """学习笔记响应"""
    model_config = ConfigDict(from_attributes=True)
    
    note_id: str
    title: Optional[str] = None
    source: str
    tags: List[str] = []
    created_at: datetime
    updated_at: datetime


# ============================================================
# 分页响应 Schema
# ============================================================

class PaginatedChatSessionsResponse(BaseModel):
    """分页会话列表响应"""
    sessions: List[ChatSessionResponse]
    total: int
    page: int = 1
    page_size: int = 50


class PaginatedChatMessagesResponse(BaseModel):
    """分页消息列表响应"""
    messages: List[ChatMessageResponse]
    total: int
    page: int = 1
    page_size: int = 50


class PaginatedLearningNotesResponse(BaseModel):
    """分页笔记列表响应"""
    notes: List[LearningNoteResponse]
    total: int
    page: int = 1
    page_size: int = 50


# ============================================================
# SSE 流式响应事件
# ============================================================

class ChatStreamEvent(BaseModel):
    """SSE 事件模型"""
    type: Literal["session_id", "content", "done", "error"]
    session_id: Optional[str] = None
    chunk: Optional[str] = None
    message_id: Optional[str] = None
    message: Optional[str] = None
