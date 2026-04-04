"""
Deer-Flow 伴学代理 API 端点
"""
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.v1.deps import CurrentActiveUser, CurrentSession, CurrentSessionTransaction
from app.config.settings import settings
from app.core.response_schema import ResponseSchemaModel, response_base
from app.db.session import async_session_maker
from app.schemas.mentor_deerflow import (
    DeerFlowMentorChatRequest,
    DeerFlowMentorMessageListResponse,
    DeerFlowMentorThreadCreateRequest,
    DeerFlowMentorThreadListResponse,
    DeerFlowMentorThreadResponse,
    DeerFlowMentorWarmupRequest,
)
from app.schemas.mentor_model import MentorModelPublicListResponse
from app.services.learning.deerflow_proxy_service import (
    DeerFlowProxyService,
    get_deerflow_proxy_service,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/learning/mentor-deerflow", tags=["mentor-deerflow"])

CurrentDeerFlowProxyService = Annotated[DeerFlowProxyService, Depends(get_deerflow_proxy_service)]


@router.post("/chat")
async def mentor_deerflow_chat(
    payload: DeerFlowMentorChatRequest,
    request: Request,
    current_user: CurrentActiveUser,
    service: CurrentDeerFlowProxyService,
) -> StreamingResponse:
    """
    Deer-Flow 伴学代理流式聊天。
    """

    async with async_session_maker() as db:
        stream_context = await service.build_chat_stream(
            db,
            current_user=current_user,
            request=payload,
        )

    return StreamingResponse(
        stream_context.stream,
        media_type="text/event-stream",
        headers=stream_context.headers,
    )


@router.post("/warmup", response_model=ResponseSchemaModel[dict])
async def warmup_mentor_deerflow_context(
    payload: DeerFlowMentorWarmupRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentActiveUser,
    service: CurrentDeerFlowProxyService,
) -> ResponseSchemaModel[dict]:
    """
    Deer-Flow 伴学上下文缓存预热。
    """

    background_tasks.add_task(
        _run_deerflow_warmup_background,
        user_id=current_user.id,
        roadmap_id=payload.roadmap_id,
        concept_id=payload.concept_id,
        concept_title=payload.concept_title,
        service=service,
    )
    return response_base.success(data={"status": "warming_up"})


@router.get("/models", response_model=ResponseSchemaModel[MentorModelPublicListResponse])
async def list_mentor_deerflow_models(
    service: CurrentDeerFlowProxyService,
    _db: CurrentSession,
    _current_user: CurrentActiveUser,
) -> ResponseSchemaModel[MentorModelPublicListResponse]:
    """
    获取 Deer-Flow 模式下可用模型列表。
    """

    items, default_model_id = await service.list_gateway_models()
    return response_base.success(
        data=MentorModelPublicListResponse(
            items=items,
            default_model_id=default_model_id or settings.DEERFLOW_DEFAULT_MODEL_NAME,
        )
    )


async def _run_deerflow_warmup_background(
    *,
    user_id: str,
    roadmap_id: str,
    concept_id: str | None,
    concept_title: str | None,
    service: DeerFlowProxyService,
) -> None:
    """
    Deer-Flow 预热后台任务。
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
            "mentor_deerflow_warmup_background_failed",
            user_id=user_id,
            roadmap_id=roadmap_id,
            error=str(exc),
        )


@router.post("/threads", response_model=ResponseSchemaModel[DeerFlowMentorThreadResponse])
async def create_mentor_deerflow_thread(
    payload: DeerFlowMentorThreadCreateRequest,
    db: CurrentSessionTransaction,
    current_user: CurrentActiveUser,
    service: CurrentDeerFlowProxyService,
) -> ResponseSchemaModel[DeerFlowMentorThreadResponse]:
    """
    创建 Deer-Flow 线程。
    """

    thread = await service.create_thread(
        db,
        current_user=current_user,
        request=payload,
    )
    return response_base.success(data=thread)


@router.get("/threads/{thread_id}", response_model=ResponseSchemaModel[DeerFlowMentorThreadResponse])
async def get_mentor_deerflow_thread(
    thread_id: str,
    db: CurrentSession,
    current_user: CurrentActiveUser,
    service: CurrentDeerFlowProxyService,
) -> ResponseSchemaModel[DeerFlowMentorThreadResponse]:
    """
    获取 Deer-Flow 线程详情。
    """

    thread = await service.get_thread(
        db,
        user_id=current_user.id,
        thread_id=thread_id,
    )
    return response_base.success(data=thread)


@router.get("/threads", response_model=ResponseSchemaModel[DeerFlowMentorThreadListResponse])
async def list_mentor_deerflow_threads(
    roadmap_id: str | None = None,
    scope: Literal["roadmap", "concept"] = "roadmap",
    concept_id: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: CurrentSession = None,
    current_user: CurrentActiveUser = None,
    service: CurrentDeerFlowProxyService = None,
) -> ResponseSchemaModel[DeerFlowMentorThreadListResponse]:
    """
    获取 Deer-Flow 线程列表。
    """

    data = await service.list_threads(
        db,
        user_id=current_user.id,
        roadmap_id=roadmap_id,
        scope=scope,
        concept_id=concept_id,
        limit=limit,
        offset=offset,
    )
    return response_base.success(data=data)


@router.get(
    "/threads/{thread_id}/messages",
    response_model=ResponseSchemaModel[DeerFlowMentorMessageListResponse],
)
async def list_mentor_deerflow_messages(
    thread_id: str,
    db: CurrentSession,
    current_user: CurrentActiveUser,
    service: CurrentDeerFlowProxyService,
) -> ResponseSchemaModel[DeerFlowMentorMessageListResponse]:
    """
    获取 Deer-Flow 线程消息快照。
    """

    data = await service.get_thread_messages(
        db,
        user_id=current_user.id,
        thread_id=thread_id,
    )
    return response_base.success(data=data)


@router.get("/threads/{thread_id}/artifacts/{artifact_path:path}")
async def get_mentor_deerflow_artifact(
    thread_id: str,
    artifact_path: str,
    download: bool = False,
    db: CurrentSession = None,
    current_user: CurrentActiveUser = None,
    service: CurrentDeerFlowProxyService = None,
) -> StreamingResponse:
    """
    代理获取 Deer-Flow 线程产物文件。
    """

    stream, content_type, headers = await service.get_thread_artifact(
        db,
        user_id=current_user.id,
        thread_id=thread_id,
        artifact_path=artifact_path,
        download=download,
    )
    return StreamingResponse(
        stream,
        media_type=content_type,
        headers=headers,
    )


@router.delete(
    "/threads/{thread_id}",
    response_model=ResponseSchemaModel[dict],
)
async def delete_mentor_deerflow_thread(
    thread_id: str,
    db: CurrentSessionTransaction,
    current_user: CurrentActiveUser,
    service: CurrentDeerFlowProxyService,
) -> ResponseSchemaModel[dict]:
    """
    删除 Deer-Flow 线程。
    """

    deleted_thread = await service.delete_thread(
        db,
        user_id=current_user.id,
        thread_id=thread_id,
    )
    return response_base.success(data={"thread_id": deleted_thread.thread_id})
