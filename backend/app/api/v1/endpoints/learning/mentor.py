"""
Mentor SSE 聊天端点。
"""
from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.v1.deps import CurrentActiveUser, CurrentSession
from app.schemas.mentor import MentorChatRequest
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

