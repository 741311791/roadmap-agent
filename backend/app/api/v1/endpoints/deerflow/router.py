"""
Deer-Flow 独立实验室 API 端点
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.v1.deps import CurrentActiveUser, CurrentSession, CurrentSessionTransaction
from app.config.settings import settings
from app.core.response_schema import ResponseSchemaModel, response_base
from app.schemas.deerflow_standalone import (
    DeerFlowStandaloneChatRequest,
    DeerFlowStandaloneThreadCreateRequest,
)
from app.schemas.mentor_deerflow import (
    DeerFlowMentorMessageListResponse,
    DeerFlowMentorThreadListResponse,
    DeerFlowMentorThreadResponse,
)
from app.schemas.mentor_model import MentorModelPublicListResponse
from app.services.learning.deerflow_proxy_service import (
    DeerFlowProxyService,
    get_deerflow_proxy_service,
)

router = APIRouter(prefix="/deerflow", tags=["deerflow-standalone"])

CurrentDeerFlowProxyService = Annotated[DeerFlowProxyService, Depends(get_deerflow_proxy_service)]


@router.post("/chat")
async def deerflow_standalone_chat(
    payload: DeerFlowStandaloneChatRequest,
    current_user: CurrentActiveUser,
    service: CurrentDeerFlowProxyService,
) -> StreamingResponse:
    """
    独立 Deer-Flow 流式聊天（用户原文上行）。
    """

    from app.db.session import async_session_maker

    async with async_session_maker() as db:
        stream_context = await service.build_standalone_chat_stream(
            db,
            current_user=current_user,
            request=payload,
        )

    return StreamingResponse(
        stream_context.stream,
        media_type="text/event-stream",
        headers=stream_context.headers,
    )


@router.get("/models", response_model=ResponseSchemaModel[MentorModelPublicListResponse])
async def list_deerflow_standalone_models(
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


@router.post("/threads", response_model=ResponseSchemaModel[DeerFlowMentorThreadResponse])
async def create_deerflow_standalone_thread(
    payload: DeerFlowStandaloneThreadCreateRequest,
    db: CurrentSessionTransaction,
    current_user: CurrentActiveUser,
    service: CurrentDeerFlowProxyService,
) -> ResponseSchemaModel[DeerFlowMentorThreadResponse]:
    """
    创建独立 Deer-Flow 线程。
    """

    thread = await service.create_standalone_thread(
        db,
        current_user=current_user,
        request=payload,
    )
    return response_base.success(data=thread)


@router.get("/threads/{thread_id}", response_model=ResponseSchemaModel[DeerFlowMentorThreadResponse])
async def get_deerflow_standalone_thread(
    thread_id: str,
    db: CurrentSession,
    current_user: CurrentActiveUser,
    service: CurrentDeerFlowProxyService,
) -> ResponseSchemaModel[DeerFlowMentorThreadResponse]:
    """
    获取独立 Deer-Flow 线程详情（与伴学共用校验：仅校验归属）。
    """

    thread = await service.get_thread(
        db,
        user_id=current_user.id,
        thread_id=thread_id,
    )
    return response_base.success(data=thread)


@router.get("/threads", response_model=ResponseSchemaModel[DeerFlowMentorThreadListResponse])
async def list_deerflow_standalone_threads(
    limit: int = 20,
    offset: int = 0,
    db: CurrentSession = None,
    current_user: CurrentActiveUser = None,
    service: CurrentDeerFlowProxyService = None,
) -> ResponseSchemaModel[DeerFlowMentorThreadListResponse]:
    """
    列出当前用户的独立 Deer-Flow 线程。
    """

    data = await service.list_standalone_threads(
        db,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return response_base.success(data=data)


@router.get(
    "/threads/{thread_id}/messages",
    response_model=ResponseSchemaModel[DeerFlowMentorMessageListResponse],
)
async def list_deerflow_standalone_messages(
    thread_id: str,
    db: CurrentSession,
    current_user: CurrentActiveUser,
    service: CurrentDeerFlowProxyService,
) -> ResponseSchemaModel[DeerFlowMentorMessageListResponse]:
    """
    获取线程消息快照。
    """

    data = await service.get_thread_messages(
        db,
        user_id=current_user.id,
        thread_id=thread_id,
    )
    return response_base.success(data=data)


@router.get("/threads/{thread_id}/artifacts/{artifact_path:path}")
async def get_deerflow_standalone_artifact(
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
async def delete_deerflow_standalone_thread(
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
