"""
伴学 Mentor API 端点

遵循企业级架构规范：API层<30行/endpoint，只负责HTTP适配
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
import structlog

from app.api.v1.deps import CurrentSession, CurrentSessionTransaction, CurrentMentorService
from app.schemas.mentor import (
    ChatStreamRequest,
    PaginatedChatSessionsResponse,
    PaginatedChatMessagesResponse,
    PaginatedLearningNotesResponse,
    LearningNoteCreate,
    LearningNoteUpdate,
    LearningNoteResponse,
)
from app.core.response_schema import response_base, ResponseSchemaModel

logger = structlog.get_logger()

router = APIRouter(prefix="/learning/mentor", tags=["mentor"])


# ============================================================
# 流式对话端点
# ============================================================

@router.post("/chat/stream")
async def chat_stream(
    request: ChatStreamRequest,
    service: CurrentMentorService,
):
    """
    伴学Agent流式对话（SSE）
    
    Args:
        request: 聊天请求
        service: Mentor服务
        
    Returns:
        SSE流响应
    """
    return StreamingResponse(
        service.chat_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



# ============================================================
# 会话管理端点
# ============================================================

@router.get("/sessions/{roadmap_id}", response_model=PaginatedChatSessionsResponse)
async def get_sessions(
    roadmap_id: str,
    user_id: str = Query(..., description="用户ID"),
    limit: int = Query(50, le=100, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    session: CurrentSession = None,
    service: CurrentMentorService = None,
):
    """获取用户的聊天会话列表"""
    sessions = await service.get_user_sessions(
        session, user_id, roadmap_id, limit, offset
    )
    return PaginatedChatSessionsResponse(
        sessions=sessions,
        total=len(sessions),
        page=offset // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.get("/messages/{session_id}", response_model=PaginatedChatMessagesResponse)
async def get_messages(
    session_id: str,
    limit: int = Query(50, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    session: CurrentSession = None,
    service: CurrentMentorService = None,
):
    """获取会话的历史消息"""
    try:
        messages = await service.get_session_messages(
            session, session_id, limit, offset
        )
        return PaginatedChatMessagesResponse(
            messages=messages,
            total=len(messages),
            page=offset // limit + 1 if limit > 0 else 1,
            page_size=limit,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============================================================
# 笔记管理端点
# ============================================================

@router.get("/notes/{roadmap_id}", response_model=PaginatedLearningNotesResponse)
async def get_notes(
    roadmap_id: str,
    user_id: str = Query(..., description="用户ID"),
    concept_id: Optional[str] = Query(None, description="概念ID（可选）"),
    limit: int = Query(50, le=200, description="返回数量限制"),
    offset: int = Query(0, ge=0, description="分页偏移"),
    session: CurrentSession = None,
    service: CurrentMentorService = None,
):
    """获取用户的学习笔记"""
    if concept_id:
        notes = await service.get_notes_by_concept(
            session, user_id, roadmap_id, concept_id, limit, offset
        )
    else:
        notes = await service.get_notes_by_roadmap(
            session, user_id, roadmap_id, limit, offset
        )
    
    return PaginatedLearningNotesResponse(
        notes=notes,
        total=len(notes),
        page=offset // limit + 1 if limit > 0 else 1,
        page_size=limit,
    )


@router.post("/notes", response_model=LearningNoteResponse)
async def create_note(
    note_data: LearningNoteCreate,
    session: CurrentSessionTransaction,
    service: CurrentMentorService = None,
):
    """创建学习笔记"""
    note = await service.create_note(session, note_data)
    # ✅ 不需要手动 commit，CurrentSessionTransaction 自动处理
    return note


@router.put("/notes/{note_id}", response_model=LearningNoteResponse)
async def update_note(
    note_id: str,
    update_data: LearningNoteUpdate,
    session: CurrentSessionTransaction,
    user_id: str = Query(..., description="用户ID"),
    service: CurrentMentorService = None,
):
    """更新学习笔记"""
    try:
        note = await service.update_note(session, note_id, user_id, update_data)
        # ✅ 不需要手动 commit，CurrentSessionTransaction 自动处理
        return note
    except ValueError as e:
        raise HTTPException(status_code=404 if "不存在" in str(e) else 403, detail=str(e))


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    session: CurrentSessionTransaction,
    user_id: str = Query(..., description="用户ID"),
    service: CurrentMentorService = None,
):
    """删除学习笔记"""
    try:
        success = await service.delete_note(session, note_id, user_id)
        # ✅ 不需要手动 commit，CurrentSessionTransaction 自动处理
        return response_base.success(data={"success": success, "message": "笔记已删除"})
    except ValueError as e:
        raise HTTPException(status_code=404 if "不存在" in str(e) else 403, detail=str(e))
