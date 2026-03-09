"""
Mentor SSE 聊天端点。
"""
from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.api.v1.deps import CurrentActiveUser, CurrentSession
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.mentor import (
    MentorAgentMode,
    MentorChatRequest,
    MentorHistoryMessageResponse,
    MentorSessionSummaryResponse,
)
from app.services.learning.mentor_service import MentorService, get_mentor_service

router = APIRouter(prefix="/learning", tags=["mentor"])


def _format_sse_event(event_name: str, payload: dict) -> str:
    """
    将事件格式化为 SSE 文本。

    Args:
        event_name: SSE 事件名。
        payload: 事件数据。

    Returns:
        str: 符合 SSE 协议的文本块。

    Raises:
        TypeError: 当 payload 不可 JSON 序列化时抛出。
    """

    return (
        f"event: {event_name}\n"
        f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    )


@router.post("/roadmaps/{roadmap_id}/mentor/chat")
async def mentor_chat(
    roadmap_id: str,
    body: MentorChatRequest,
    user: CurrentActiveUser,
    db: CurrentSession,
) -> StreamingResponse:
    """
    Mentor 流式聊天接口（SSE）。

    Args:
        roadmap_id: 路线图 ID。
        body: 聊天请求体。
        user: 当前登录用户。
        db: 只读数据库会话。

    Returns:
        StreamingResponse: SSE 流式响应。

    Raises:
        无。
    """

    mentor_service: MentorService = get_mentor_service()

    async def event_generator() -> AsyncGenerator[str, None]:
        """
        SSE 事件生成器。

        Args:
            无。

        Returns:
            AsyncGenerator[str, None]: SSE 事件文本流。

        Raises:
            无。
        """

        try:
            async for event in mentor_service.stream_chat(
                db=db,
                user_id=user.id,
                roadmap_id=roadmap_id,
                messages=body.messages,
                agent_mode=body.agent_mode,
                concept_id=body.concept_id,
                session_id=body.session_id,
            ):
                event_name = str(event.get("type", "message"))
                yield _format_sse_event(event_name=event_name, payload=event)
        except Exception as exc:  # pragma: no cover - SSE 兜底保护
            error_payload = {
                "type": "error",
                "message": str(exc),
            }
            yield _format_sse_event(event_name="error", payload=error_payload)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get(
    "/roadmaps/{roadmap_id}/mentor/sessions",
    response_model=ResponseSchemaModel[list[MentorSessionSummaryResponse]],
)
async def list_mentor_sessions(
    roadmap_id: str,
    user: CurrentActiveUser,
    db: CurrentSession,
    agent_mode: MentorAgentMode | None = Query(default=None, description="可选模式过滤"),
    limit: int = Query(default=20, ge=1, le=100, description="返回数量"),
) -> ResponseSchemaModel[list[MentorSessionSummaryResponse]]:
    """
    获取当前用户在指定路线图下的 Mentor 会话列表。
    """
    mentor_service: MentorService = get_mentor_service()
    sessions = await mentor_service.list_sessions(
        db=db,
        user_id=user.id,
        roadmap_id=roadmap_id,
        agent_mode=agent_mode,
        limit=limit,
    )
    return response_base.success(data=sessions)


@router.get(
    "/roadmaps/{roadmap_id}/mentor/sessions/{session_id}/messages",
    response_model=ResponseSchemaModel[list[MentorHistoryMessageResponse]],
)
async def get_mentor_session_messages(
    roadmap_id: str,
    session_id: str,
    user: CurrentActiveUser,
    db: CurrentSession,
    limit: int = Query(default=200, ge=1, le=500, description="返回数量"),
) -> ResponseSchemaModel[list[MentorHistoryMessageResponse]]:
    """
    获取 Mentor 会话历史消息。
    """
    mentor_service: MentorService = get_mentor_service()
    history_messages = await mentor_service.get_session_messages(
        db=db,
        user_id=user.id,
        roadmap_id=roadmap_id,
        session_id=session_id,
        limit=limit,
    )
    return response_base.success(data=history_messages)

