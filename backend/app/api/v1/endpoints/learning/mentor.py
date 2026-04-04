"""
AI 伴学助手 API 端点
"""
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.v1.deps import CurrentActiveUser, CurrentSession, CurrentSessionTransaction
from app.core.response_schema import ResponseSchemaModel, response_base
from app.db.session import async_session_maker
from app.models.database import ChatMessage, ChatSession, MentorMemoryJob
from app.schemas.mentor import (
    MentorChatMessageResponse,
    MentorChatRequest,
    MentorMemoryJobResponse,
    MentorMessageListResponse,
    MentorSessionCreateRequest,
    MentorSessionListResponse,
    MentorSessionResponse,
    MentorWarmupRequest,
)
from app.schemas.mentor_model import MentorModelPublicListResponse
from app.services.learning.mentor_service import MentorService, get_mentor_service

logger = structlog.get_logger()

router = APIRouter(prefix="/learning/mentor", tags=["mentor"])

CurrentMentorService = Annotated[MentorService, Depends(get_mentor_service)]


@router.post("/chat")
async def mentor_chat(
    payload: MentorChatRequest,
    request: Request,
    current_user: CurrentActiveUser,
    service: CurrentMentorService,
) -> StreamingResponse:
    """
    AI 伴学助手流式聊天

    注意：DB session 仅在预处理阶段（build_chat_stream）持有，
    预处理完成后立即关闭，不再占用连接池资源至整个 SSE 流结束。
    """
    client_ip = request.client.host if request.client else None
    async with async_session_maker() as db:
        stream_context = await service.build_chat_stream(
            db=db,
            current_user=current_user,
            request=payload,
            client_ip=client_ip,
        )
    return StreamingResponse(
        stream_context.stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/warmup", response_model=ResponseSchemaModel[dict])
async def warmup_mentor_context(
    payload: MentorWarmupRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentActiveUser,
    service: CurrentMentorService,
) -> ResponseSchemaModel[dict]:
    """
    AI 伴学助手缓存预热

    在用户进入路线图详情页或切换章节时调用，将学习上下文和长期记忆写入 Redis，
    供后续对话直接读取，彻底消除 Mem0 向量搜索和数据库查询延迟。

    此接口为幂等操作，前端可无顾虑地多次调用（重复调用只会刷新 TTL）。

    实现说明：使用 FastAPI BackgroundTasks（而非 asyncio.create_task）并在任务内独立
    创建 DB session，避免使用请求级 session（请求结束后 session 已关闭）。
    """
    background_tasks.add_task(
        _run_warmup_background,
        user_id=current_user.id,
        roadmap_id=payload.roadmap_id,
        concept_id=payload.concept_id,
        concept_title=payload.concept_title,
        service=service,
    )
    return response_base.success(data={"status": "warming_up"})


@router.get("/models", response_model=ResponseSchemaModel[MentorModelPublicListResponse])
async def list_mentor_models(
    db: CurrentSession,
    current_user: CurrentActiveUser,
    service: CurrentMentorService,
) -> ResponseSchemaModel[MentorModelPublicListResponse]:
    """
    获取 Mentor 可用模型列表
    """
    items, default_model_id = await service.list_available_models(
        db,
        user_id=current_user.id,
    )
    return response_base.success(
        data=MentorModelPublicListResponse(
            items=items,
            default_model_id=default_model_id,
        )
    )


async def _run_warmup_background(
    *,
    user_id: str,
    roadmap_id: str,
    concept_id: str | None,
    concept_title: str | None,
    service: MentorService,
) -> None:
    """
    独立的后台预热协程，使用自己的 DB session，不依赖请求级 session
    """
    try:
        async with async_session_maker() as db:
            await service.warmup_context_cache(
                db,
                user_id=user_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                concept_title=concept_title,
            )
    except Exception as exc:
        logger.warning(
            "mentor_warmup_background_failed",
            user_id=user_id,
            roadmap_id=roadmap_id,
            error=str(exc),
        )


@router.post("/sessions", response_model=ResponseSchemaModel[MentorSessionResponse])
async def create_mentor_session(
    payload: MentorSessionCreateRequest,
    db: CurrentSession,
    current_user: CurrentActiveUser,
    service: CurrentMentorService,
) -> ResponseSchemaModel[MentorSessionResponse]:
    """
    创建 AI 伴学助手会话
    """
    chat_session = await service.create_session(
        db=db,
        user_id=current_user.id,
        roadmap_id=payload.roadmap_id,
        concept_id=payload.concept_id,
        title=payload.title,
        agent_type=payload.agent_kind,
        model_id=payload.model_id,
    )
    return response_base.success(data=_serialize_session(chat_session))


@router.get("/sessions/{session_id}", response_model=ResponseSchemaModel[MentorSessionResponse])
async def get_mentor_session(
    session_id: str,
    db: CurrentSession,
    current_user: CurrentActiveUser,
    service: CurrentMentorService,
) -> ResponseSchemaModel[MentorSessionResponse]:
    """
    获取 AI 伴学助手会话详情
    """
    chat_session = await service.get_session(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )
    return response_base.success(data=_serialize_session(chat_session))


@router.get("/sessions", response_model=ResponseSchemaModel[MentorSessionListResponse])
async def list_mentor_sessions(
    roadmap_id: str | None = None,
    scope: Literal["roadmap", "concept"] = "roadmap",
    concept_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: CurrentSession = None,
    current_user: CurrentActiveUser = None,
    service: CurrentMentorService = None,
) -> ResponseSchemaModel[MentorSessionListResponse]:
    """
    获取 AI 伴学助手会话列表
    """
    sessions, total = await service.list_sessions(
        db,
        user_id=current_user.id,
        roadmap_id=roadmap_id,
        scope=scope,
        concept_id=concept_id,
        limit=limit,
        offset=offset,
    )
    return response_base.success(
        data=MentorSessionListResponse(
            items=[_serialize_session(item) for item in sessions],
            total=total,
        )
    )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ResponseSchemaModel[MentorMessageListResponse],
)
async def list_mentor_messages(
    session_id: str,
    limit: int = 100,
    offset: int = 0,
    db: CurrentSession = None,
    current_user: CurrentActiveUser = None,
    service: CurrentMentorService = None,
) -> ResponseSchemaModel[MentorMessageListResponse]:
    """
    获取 AI 伴学助手会话消息列表
    """
    _, messages, total = await service.get_session_messages(
        db,
        user_id=current_user.id,
        session_id=session_id,
        limit=limit,
        offset=offset,
    )
    return response_base.success(
        data=MentorMessageListResponse(
            items=[_serialize_message(item) for item in messages],
            total=total,
        )
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=ResponseSchemaModel[dict],
)
async def delete_mentor_session(
    session_id: str,
    db: CurrentSessionTransaction,
    current_user: CurrentActiveUser,
    service: CurrentMentorService,
) -> ResponseSchemaModel[dict]:
    """
    删除 AI 伴学助手会话
    """
    deleted_session = await service.delete_session(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )
    return response_base.success(
        data={
            "session_id": deleted_session.session_id,
        }
    )


@router.post(
    "/sessions/{session_id}/rebuild-stm",
    response_model=ResponseSchemaModel[dict],
)
async def rebuild_mentor_short_term_memory(
    session_id: str,
    db: CurrentSession,
    current_user: CurrentActiveUser,
    service: CurrentMentorService,
) -> ResponseSchemaModel[dict]:
    """
    重建 AI 伴学助手短期记忆窗口
    """
    rebuilt_count = await service.rebuild_short_term_memory(
        db,
        user_id=current_user.id,
        session_id=session_id,
    )
    return response_base.success(
        data={
            "session_id": session_id,
            "rebuilt_count": rebuilt_count,
        }
    )


@router.get(
    "/memory-jobs/{job_id}",
    response_model=ResponseSchemaModel[MentorMemoryJobResponse],
)
async def get_mentor_memory_job(
    job_id: str,
    db: CurrentSession,
    current_user: CurrentActiveUser,
    service: CurrentMentorService,
) -> ResponseSchemaModel[MentorMemoryJobResponse]:
    """
    获取 AI 伴学助手记忆任务状态
    """
    job = await service.get_memory_job(
        db,
        user_id=current_user.id,
        job_id=job_id,
    )
    return response_base.success(data=_serialize_memory_job(job))


@router.post(
    "/messages/{message_id}/replay-memory-job",
    response_model=ResponseSchemaModel[MentorMemoryJobResponse],
)
async def replay_mentor_memory_job(
    message_id: str,
    db: CurrentSession,
    current_user: CurrentActiveUser,
    service: CurrentMentorService,
) -> ResponseSchemaModel[MentorMemoryJobResponse]:
    """
    重放 AI 伴学助手记忆任务
    """
    job = await service.replay_memory_job(
        db,
        user_id=current_user.id,
        message_id=message_id,
    )
    return response_base.success(data=_serialize_memory_job(job))


def _serialize_session(chat_session: ChatSession) -> MentorSessionResponse:
    """
    序列化会话响应
    """

    normalized_agent_kind = _normalize_agent_kind(chat_session.agent_type)
    return MentorSessionResponse(
        session_id=chat_session.session_id,
        user_id=chat_session.user_id,
        roadmap_id=chat_session.roadmap_id,
        concept_id=chat_session.concept_id,
        title=chat_session.title,
        agent_kind=normalized_agent_kind,
        qa_style="casual" if normalized_agent_kind == "qa" else None,
        model_id=chat_session.model_id,
        message_count=chat_session.message_count,
        last_message_preview=chat_session.last_message_preview,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
    )


def _serialize_message(chat_message: ChatMessage) -> MentorChatMessageResponse:
    """
    序列化消息响应
    """
    metadata = chat_message.message_metadata or {}
    normalized_agent_kind = _normalize_agent_kind(chat_message.agent_type, allow_none=True)
    return MentorChatMessageResponse(
        message_id=chat_message.message_id,
        session_id=chat_message.session_id,
        role=chat_message.role,
        content=chat_message.content,
        agent_kind=normalized_agent_kind,
        qa_style=metadata.get("qaStyle") or metadata.get("qa_style"),
        model_id=chat_message.model_id,
        trace_id=chat_message.trace_id,
        message_metadata=chat_message.message_metadata,
        created_at=chat_message.created_at,
    )


def _serialize_memory_job(job: MentorMemoryJob) -> MentorMemoryJobResponse:
    """
    序列化记忆任务响应
    """
    return MentorMemoryJobResponse(
        job_id=job.job_id,
        message_id=job.message_id,
        session_id=job.session_id,
        user_id=job.user_id,
        celery_task_id=job.celery_task_id,
        status=job.status,
        retry_count=job.retry_count,
        last_error=job.last_error,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _normalize_agent_kind(agent_type: str | None, *, allow_none: bool = False) -> Literal["qa", "guide", "quiz"] | None:
    """
    兼容历史 `agent_type` 值，统一映射到新的 `agent_kind`
    """

    normalized_agent_type = (agent_type or "").strip().lower()
    if normalized_agent_type in {"qa", "guide", "quiz"}:
        return normalized_agent_type

    if normalized_agent_type in {"company", "tutoring"}:
        return "qa"

    return None if allow_none else "qa"
