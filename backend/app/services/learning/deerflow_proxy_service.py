"""
Deer-Flow 代理服务
"""
from __future__ import annotations

import json
import mimetypes
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, AsyncGenerator

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.custom_exceptions import errors
from app.crud.crud_roadmap_chat_thread import (
    RoadmapChatThreadCRUD,
    get_roadmap_chat_thread_crud,
)
from app.db.session import async_session_maker
from app.models.database import RoadmapChatThread, User, beijing_now
from app.schemas.deerflow_standalone import (
    DeerFlowStandaloneChatRequest,
    DeerFlowStandaloneThreadCreateRequest,
)
from app.schemas.mentor_deerflow import (
    DeerFlowMentorChatRequest,
    DeerFlowMentorMessageListResponse,
    DeerFlowMentorMessageResponse,
    DeerFlowMentorThreadCreateRequest,
    DeerFlowMentorThreadListResponse,
    DeerFlowMentorThreadResponse,
)
from app.services.learning.deerflow_context_service import (
    DeerFlowContextService,
    DeerFlowPreparedChatPayload,
    get_deerflow_context_service,
)
from app.services.shared.mentor_model_registry_service import (
    MentorModelRegistryService,
    get_mentor_model_registry_service,
)
from app.schemas.mentor_model import MentorModelPublicItem

logger = structlog.get_logger()


@dataclass(slots=True)
class DeerFlowMentorChatStreamContext:
    """
    Deer-Flow 代理流式上下文

    Args:
        thread_id: 线程 ID
        stream: SSE 字节流
        headers: 需要透传给前端的响应头

    Returns:
        None

    Raises:
        None
    """

    thread_id: str
    stream: AsyncGenerator[bytes, None]
    headers: dict[str, str]


class DeerFlowProxyService:
    """
    负责在主应用与 Deer-Flow 之间做代理转发。
    """

    def __init__(
        self,
        context_service: DeerFlowContextService | None = None,
        roadmap_chat_thread_crud: RoadmapChatThreadCRUD | None = None,
        model_registry_service: MentorModelRegistryService | None = None,
    ) -> None:
        """
        初始化代理服务。

        Args:
            context_service: Deer-Flow 上下文服务。
            roadmap_chat_thread_crud: 线程映射 CRUD。
            model_registry_service: 模型注册表服务。

        Returns:
            None

        Raises:
            None
        """

        self.context_service = context_service or get_deerflow_context_service()
        self.roadmap_chat_thread_crud = roadmap_chat_thread_crud or get_roadmap_chat_thread_crud()
        self.model_registry_service = model_registry_service or get_mentor_model_registry_service()

    async def list_available_models(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> tuple[list, str | None]:
        """
        获取 Deer-Flow 模式下可选模型列表。

        Args:
            db: 数据库会话。
            user_id: 当前用户 ID。

        Returns:
            模型列表与默认模型 ID。

        Raises:
            None
        """

        return await self.model_registry_service.list_available_models(
            db,
            user_id=user_id,
        )

    async def list_gateway_models(self) -> tuple[list[MentorModelPublicItem], str | None]:
        """
        获取 Deer-Flow gateway 当前真实可用模型列表。

        Args:
            None

        Returns:
            模型列表与默认模型名。

        Raises:
            ExternalServiceError: 上游拉取失败。
        """

        client = self._build_http_client(streaming=False)
        try:
            response = await client.get(
                "/api/models",
                headers=self._build_upstream_headers(),
            )
        except httpx.TimeoutException as exc:
            raise errors.TimeoutError(msg="Deer-Flow 模型列表请求超时") from exc
        except httpx.HTTPError as exc:
            raise errors.ExternalServiceError(msg="无法连接 Deer-Flow 服务") from exc
        finally:
            await client.aclose()

        if response.status_code >= 400:
            detail = await self._read_upstream_error(response)
            raise errors.ExternalServiceError(msg=detail)

        payload = response.json()
        raw_models = payload.get("models") if isinstance(payload, dict) else []
        items: list[MentorModelPublicItem] = []
        default_model_id: str | None = None

        if isinstance(raw_models, list):
            for index, raw_model in enumerate(raw_models):
                if not isinstance(raw_model, dict):
                    continue

                model_name = str(raw_model.get("name") or "").strip()
                if not model_name:
                    continue

                is_default = model_name == settings.DEERFLOW_DEFAULT_MODEL_NAME or (
                    default_model_id is None and index == 0
                )
                if is_default:
                    default_model_id = model_name

                items.append(
                    MentorModelPublicItem(
                        model_id=model_name,
                        display_name=str(raw_model.get("display_name") or model_name),
                        description=raw_model.get("description"),
                        provider=str(raw_model.get("provider") or "deerflow"),
                        is_default=is_default,
                        supports_thinking=bool(raw_model.get("supports_thinking", False)),
                        supports_reasoning_effort=bool(raw_model.get("supports_reasoning_effort", False)),
                    )
                )

        return items, default_model_id

    async def warmup_context_cache(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        roadmap_id: str,
        concept_id: str | None,
        concept_title: str | None,
    ) -> dict[str, object]:
        """
        预热 Deer-Flow 模式所需缓存。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            roadmap_id: 路线图 ID。
            concept_id: 概念 ID。
            concept_title: 概念标题。

        Returns:
            预热摘要。

        Raises:
            NotFoundError: 路线图不存在。
            ForbiddenError: 当前用户无权访问路线图。
        """

        return await self.context_service.warmup_context_cache(
            db,
            user_id=user_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            concept_title=concept_title,
        )

    async def create_thread(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        request: DeerFlowMentorThreadCreateRequest,
    ) -> DeerFlowMentorThreadResponse:
        """
        创建 Deer-Flow 线程及本地映射。

        Args:
            db: 数据库会话。
            current_user: 当前用户。
            request: 线程创建请求。

        Returns:
            创建后的线程响应。

        Raises:
            NotFoundError: 路线图不存在。
            ForbiddenError: 当前用户无权访问路线图。
            ExternalServiceError: 上游 Deer-Flow 创建失败。
        """

        _, title = await self.context_service.prepare_thread_create_context(
            db,
            current_user=current_user,
            request=request,
        )
        thread_id = str(uuid.uuid4())
        await self._create_upstream_thread(
            thread_id=thread_id,
            metadata={
                "user_id": current_user.id,
                "roadmap_id": request.roadmap_id,
                "stage_id": request.stage_id,
                "task_id": request.task_id,
                "concept_id": request.concept_id,
                "source": "roadmap_agent",
            },
        )
        async with async_session_maker.begin() as session:
            thread = await self.roadmap_chat_thread_crud.create_thread(
                session,
                thread_id=thread_id,
                user_id=current_user.id,
                roadmap_id=request.roadmap_id,
                stage_id=request.stage_id,
                task_id=request.task_id,
                concept_id=request.concept_id,
                title=title,
                assistant_id=request.assistant_id or settings.DEERFLOW_DEFAULT_ASSISTANT_ID,
                model_id=request.model_id,
                metadata_json={
                    "status": "idle",
                },
            )
        return self._serialize_thread(thread)

    async def list_threads(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        roadmap_id: str | None = None,
        scope: str = "roadmap",
        concept_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> DeerFlowMentorThreadListResponse:
        """
        获取当前用户的 Deer-Flow 线程列表。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            roadmap_id: 路线图 ID。
            scope: 查询作用域。
            concept_id: 概念 ID。
            limit: 返回数量。
            offset: 分页偏移。

        Returns:
            线程列表响应。

        Raises:
            RequestError: concept 作用域缺少 concept_id。
        """

        if scope == "concept" and not concept_id:
            raise errors.RequestError(msg="concept scope requires concept_id")

        threads = await self.roadmap_chat_thread_crud.list_user_threads(
            db,
            user_id=user_id,
            roadmap_id=roadmap_id,
            scope=scope,
            concept_id=concept_id,
            limit=limit,
            offset=offset,
        )
        total = await self.roadmap_chat_thread_crud.count_user_threads(
            db,
            user_id=user_id,
            roadmap_id=roadmap_id,
            scope=scope,
            concept_id=concept_id,
        )
        return DeerFlowMentorThreadListResponse(
            items=[self._serialize_thread(item) for item in threads],
            total=total,
        )

    async def list_standalone_threads(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> DeerFlowMentorThreadListResponse:
        """
        列出当前用户的独立 Deer-Flow 实验室线程（roadmap_id 与 concept_id 均为空）。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            limit: 返回数量。
            offset: 分页偏移。

        Returns:
            线程列表响应。

        Raises:
            None
        """

        threads = await self.roadmap_chat_thread_crud.list_user_threads(
            db,
            user_id=user_id,
            standalone_only=True,
            limit=limit,
            offset=offset,
        )
        total = await self.roadmap_chat_thread_crud.count_user_threads(
            db,
            user_id=user_id,
            standalone_only=True,
        )
        return DeerFlowMentorThreadListResponse(
            items=[self._serialize_thread(item) for item in threads],
            total=total,
        )

    async def create_standalone_thread(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        request: DeerFlowStandaloneThreadCreateRequest,
    ) -> DeerFlowMentorThreadResponse:
        """
        创建独立 Deer-Flow 线程及本地映射（无路线图）。

        Args:
            db: 数据库会话。
            current_user: 当前用户。
            request: 线程创建请求。

        Returns:
            创建后的线程响应。

        Raises:
            ExternalServiceError: 上游创建失败。
        """

        title = self.context_service.prepare_standalone_thread_title(request=request)
        thread_id = str(uuid.uuid4())
        await self._create_upstream_thread(
            thread_id=thread_id,
            metadata={
                "user_id": current_user.id,
                "source": "deerflow_standalone",
            },
        )
        async with async_session_maker.begin() as session:
            thread = await self.roadmap_chat_thread_crud.create_thread(
                session,
                thread_id=thread_id,
                user_id=current_user.id,
                roadmap_id=None,
                title=title,
                assistant_id=request.assistant_id or settings.DEERFLOW_DEFAULT_ASSISTANT_ID,
                model_id=request.model_id,
                metadata_json={
                    "status": "idle",
                },
            )
        return self._serialize_thread(thread)

    async def get_thread(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        thread_id: str,
    ) -> DeerFlowMentorThreadResponse:
        """
        获取单个线程详情。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            thread_id: 线程 ID。

        Returns:
            线程响应。

        Raises:
            NotFoundError: 线程不存在或不属于当前用户。
        """

        thread = await self._get_owned_thread(
            db,
            user_id=user_id,
            thread_id=thread_id,
        )
        return self._serialize_thread(thread)

    async def get_thread_messages(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        thread_id: str,
    ) -> DeerFlowMentorMessageListResponse:
        """
        获取线程当前消息快照。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            thread_id: 线程 ID。

        Returns:
            消息列表响应。

        Raises:
            NotFoundError: 线程不存在或不属于当前用户。
            ExternalServiceError: Deer-Flow 拉取状态失败。
        """

        thread = await self._get_owned_thread(
            db,
            user_id=user_id,
            thread_id=thread_id,
        )
        state = await self._fetch_upstream_thread_state(thread_id)
        upstream_messages = state.get("values", {}).get("messages", [])
        messages = self._map_upstream_messages_to_responses(
            thread=thread,
            upstream_messages=upstream_messages if isinstance(upstream_messages, list) else [],
        )
        return DeerFlowMentorMessageListResponse(
            items=messages,
            total=len(messages),
        )

    async def get_thread_artifact(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        thread_id: str,
        artifact_path: str,
        download: bool = False,
    ) -> tuple[AsyncGenerator[bytes, None], str, dict[str, str]]:
        """
        代理获取 Deer-Flow 线程产物文件。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            thread_id: 线程 ID。
            artifact_path: 产物相对路径或绝对虚拟路径。
            download: 是否强制下载。

        Returns:
            文件字节流、媒体类型与响应头。

        Raises:
            NotFoundError: 线程不存在。
            ExternalServiceError: 上游产物拉取失败。
        """

        thread = await self._get_owned_thread(
            db,
            user_id=user_id,
            thread_id=thread_id,
        )
        normalized_path = artifact_path if artifact_path.startswith("/") else f"/{artifact_path}"
        client = self._build_http_client(streaming=True)
        request_url = f"/api/threads/{thread.thread_id}/artifacts{normalized_path}"
        if download:
            request_url = f"{request_url}?download=true"

        try:
            upstream_request = client.build_request(
                "GET",
                request_url,
                headers=self._build_upstream_headers(),
            )
            upstream_response = await client.send(
                upstream_request,
                stream=True,
            )
        except httpx.TimeoutException as exc:
            await client.aclose()
            raise errors.TimeoutError(msg="Deer-Flow 产物请求超时") from exc
        except httpx.HTTPError as exc:
            await client.aclose()
            raise errors.ExternalServiceError(msg="无法连接 Deer-Flow 服务") from exc

        if upstream_response.status_code >= 400:
            detail = await self._read_upstream_error(upstream_response)
            await upstream_response.aclose()
            await client.aclose()
            raise errors.ExternalServiceError(msg=detail)

        content_type = upstream_response.headers.get("content-type")
        if not content_type:
            content_type = mimetypes.guess_type(normalized_path)[0] or "application/octet-stream"

        response_headers: dict[str, str] = {}
        content_disposition = upstream_response.headers.get("content-disposition")
        cache_control = upstream_response.headers.get("cache-control")
        if content_disposition:
            response_headers["Content-Disposition"] = content_disposition
        if cache_control:
            response_headers["Cache-Control"] = cache_control

        async def artifact_stream() -> AsyncGenerator[bytes, None]:
            try:
                async for chunk in upstream_response.aiter_bytes():
                    yield chunk
            finally:
                try:
                    await upstream_response.aclose()
                finally:
                    await client.aclose()

        return artifact_stream(), content_type, response_headers

    async def delete_thread(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        thread_id: str,
    ) -> RoadmapChatThread:
        """
        删除 Deer-Flow 线程及本地映射。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            thread_id: 线程 ID。

        Returns:
            被删除的线程记录。

        Raises:
            NotFoundError: 线程不存在或不属于当前用户。
            ExternalServiceError: 上游 Deer-Flow 删除失败。
        """

        thread = await self._get_owned_thread(
            db,
            user_id=user_id,
            thread_id=thread_id,
        )
        await self._delete_upstream_thread(thread_id)
        deleted = await self.roadmap_chat_thread_crud.delete_thread(
            db,
            thread_id=thread_id,
        )
        return deleted or thread

    async def build_chat_stream(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        request: DeerFlowMentorChatRequest,
    ) -> DeerFlowMentorChatStreamContext:
        """
        构建 Deer-Flow 聊天流。

        Args:
            db: 数据库会话。
            current_user: 当前用户。
            request: 聊天请求。

        Returns:
            流式上下文。

        Raises:
            NotFoundError: 路线图或线程不存在。
            ForbiddenError: 当前用户无权访问路线图。
            ExternalServiceError: Deer-Flow 上游调用失败。
            TimeoutError: 上游请求超时。
        """

        prepared = await self.context_service.prepare_chat_payload(
            db,
            current_user=current_user,
            request=request,
        )

        if request.thread_id:
            thread = await self._get_owned_thread(
                db,
                user_id=current_user.id,
                thread_id=request.thread_id,
            )
        else:
            thread = await self._create_thread_for_chat(
                current_user=current_user,
                request=request,
                prepared=prepared,
            )

        await self._ensure_upstream_thread_exists(thread)
        client = self._build_http_client(streaming=True)

        payload = {
            "assistant_id": prepared.assistant_id,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prepared.upstream_message,
                    }
                ]
            },
            "metadata": prepared.metadata,
            "context": prepared.runtime_context,
            "stream_mode": ["messages-tuple", "values"],
            "on_disconnect": "continue",
        }

        request_url = f"/api/threads/{thread.thread_id}/runs/stream"
        try:
            upstream_request = client.build_request(
                "POST",
                request_url,
                headers=self._build_upstream_headers(),
                json=payload,
            )
            upstream_response = await client.send(
                upstream_request,
                stream=True,
            )
        except httpx.TimeoutException as exc:
            await client.aclose()
            raise errors.TimeoutError(msg="Deer-Flow 流式请求超时") from exc
        except httpx.HTTPError as exc:
            await client.aclose()
            raise errors.ExternalServiceError(msg="无法连接 Deer-Flow 服务") from exc

        if upstream_response.status_code >= 400:
            detail = await self._read_upstream_error(upstream_response)
            await upstream_response.aclose()
            await client.aclose()
            raise errors.ExternalServiceError(msg=detail)

        headers = {
            "Cache-Control": upstream_response.headers.get("cache-control", "no-cache"),
            "Connection": upstream_response.headers.get("connection", "keep-alive"),
            "X-Accel-Buffering": upstream_response.headers.get("x-accel-buffering", "no"),
        }
        content_location = upstream_response.headers.get("content-location")
        if content_location:
            headers["Content-Location"] = content_location

        async def event_stream() -> AsyncGenerator[bytes, None]:
            """
            透传上游 SSE，并在结束后同步线程状态。

            Args:
                None

            Returns:
                SSE 字节流。

            Raises:
                None
            """

            try:
                async for chunk in upstream_response.aiter_bytes():
                    yield chunk
            finally:
                try:
                    await upstream_response.aclose()
                finally:
                    await client.aclose()
                await self._sync_thread_after_stream(
                    thread_id=thread.thread_id,
                    fallback_title=prepared.title,
                    fallback_model_id=prepared.model_id,
                    fallback_assistant_id=prepared.assistant_id,
                )

        return DeerFlowMentorChatStreamContext(
            thread_id=thread.thread_id,
            stream=event_stream(),
            headers=headers,
        )

    async def build_standalone_chat_stream(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        request: DeerFlowStandaloneChatRequest,
    ) -> DeerFlowMentorChatStreamContext:
        """
        构建独立 Deer-Flow 实验室聊天流（用户原文上行，无学习上下文）。

        Args:
            db: 数据库会话。
            current_user: 当前用户。
            request: 独立聊天请求。

        Returns:
            流式上下文。

        Raises:
            RequestError: 线程不属于独立模式或参数错误。
            NotFoundError: 线程不存在。
            ExternalServiceError: 上游调用失败。
        """

        prepared = await self.context_service.prepare_standalone_chat_payload(
            db,
            current_user=current_user,
            request=request,
        )

        if request.thread_id:
            thread = await self._get_owned_standalone_thread(
                db,
                user_id=current_user.id,
                thread_id=request.thread_id,
            )
        else:
            thread = await self._create_thread_for_standalone_chat(
                current_user=current_user,
                prepared=prepared,
            )

        await self._ensure_upstream_thread_exists(thread)
        client = self._build_http_client(streaming=True)

        payload = {
            "assistant_id": prepared.assistant_id,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": prepared.upstream_message,
                    }
                ]
            },
            "metadata": prepared.metadata,
            "context": prepared.runtime_context,
            "stream_mode": ["messages-tuple", "values"],
            "on_disconnect": "continue",
        }

        request_url = f"/api/threads/{thread.thread_id}/runs/stream"
        try:
            upstream_request = client.build_request(
                "POST",
                request_url,
                headers=self._build_upstream_headers(),
                json=payload,
            )
            upstream_response = await client.send(
                upstream_request,
                stream=True,
            )
        except httpx.TimeoutException as exc:
            await client.aclose()
            raise errors.TimeoutError(msg="Deer-Flow 流式请求超时") from exc
        except httpx.HTTPError as exc:
            await client.aclose()
            raise errors.ExternalServiceError(msg="无法连接 Deer-Flow 服务") from exc

        if upstream_response.status_code >= 400:
            detail = await self._read_upstream_error(upstream_response)
            await upstream_response.aclose()
            await client.aclose()
            raise errors.ExternalServiceError(msg=detail)

        headers = {
            "Cache-Control": upstream_response.headers.get("cache-control", "no-cache"),
            "Connection": upstream_response.headers.get("connection", "keep-alive"),
            "X-Accel-Buffering": upstream_response.headers.get("x-accel-buffering", "no"),
        }
        content_location = upstream_response.headers.get("content-location")
        if content_location:
            headers["Content-Location"] = content_location

        async def event_stream() -> AsyncGenerator[bytes, None]:
            """
            透传上游 SSE，并在结束后同步线程状态。

            Args:
                None

            Returns:
                SSE 字节流。

            Raises:
                None
            """

            try:
                async for chunk in upstream_response.aiter_bytes():
                    yield chunk
            finally:
                try:
                    await upstream_response.aclose()
                finally:
                    await client.aclose()
                await self._sync_thread_after_stream(
                    thread_id=thread.thread_id,
                    fallback_title=prepared.title,
                    fallback_model_id=prepared.model_id,
                    fallback_assistant_id=prepared.assistant_id,
                )

        return DeerFlowMentorChatStreamContext(
            thread_id=thread.thread_id,
            stream=event_stream(),
            headers=headers,
        )

    async def _create_thread_for_chat(
        self,
        *,
        current_user: User,
        request: DeerFlowMentorChatRequest,
        prepared: DeerFlowPreparedChatPayload,
    ) -> RoadmapChatThread:
        """
        为首次聊天创建本地线程映射。

        Args:
            current_user: 当前用户。
            request: 聊天请求。
            prepared: 预处理聊天载荷。

        Returns:
            本地线程记录。

        Raises:
            None
        """

        thread_id = str(uuid.uuid4())
        await self._create_upstream_thread(
            thread_id=thread_id,
            metadata={
                "user_id": current_user.id,
                "roadmap_id": request.context.roadmap_id,
                "stage_id": request.context.stage_id,
                "task_id": request.context.task_id,
                "concept_id": request.context.concept_id,
                "source": "roadmap_agent",
            },
        )
        async with async_session_maker.begin() as session:
            return await self.roadmap_chat_thread_crud.create_thread(
                session,
                thread_id=thread_id,
                user_id=current_user.id,
                roadmap_id=request.context.roadmap_id,
                stage_id=request.context.stage_id,
                task_id=request.context.task_id,
                concept_id=request.context.concept_id,
                title=prepared.title,
                assistant_id=prepared.assistant_id,
                model_id=prepared.model_id,
                metadata_json={
                    "status": "idle",
                },
            )

    async def _create_thread_for_standalone_chat(
        self,
        *,
        current_user: User,
        prepared: DeerFlowPreparedChatPayload,
    ) -> RoadmapChatThread:
        """
        为独立模式首次聊天创建本地线程映射。

        Args:
            current_user: 当前用户。
            prepared: 预处理聊天载荷。

        Returns:
            本地线程记录。

        Raises:
            None
        """

        thread_id = str(uuid.uuid4())
        await self._create_upstream_thread(
            thread_id=thread_id,
            metadata={
                "user_id": current_user.id,
                "source": "deerflow_standalone",
            },
        )
        async with async_session_maker.begin() as session:
            return await self.roadmap_chat_thread_crud.create_thread(
                session,
                thread_id=thread_id,
                user_id=current_user.id,
                roadmap_id=None,
                title=prepared.title,
                assistant_id=prepared.assistant_id,
                model_id=prepared.model_id,
                metadata_json={
                    "status": "idle",
                },
            )

    async def _get_owned_standalone_thread(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        thread_id: str,
    ) -> RoadmapChatThread:
        """
        校验线程归属且必须为独立实验室线程。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            thread_id: 线程 ID。

        Returns:
            线程记录。

        Raises:
            NotFoundError: 线程不存在。
            RequestError: 线程绑定了路线图或概念（非独立模式）。
        """

        thread = await self._get_owned_thread(
            db,
            user_id=user_id,
            thread_id=thread_id,
        )
        if thread.roadmap_id is not None or thread.concept_id is not None:
            raise errors.RequestError(msg="该线程不属于独立 DeerFlow 实验室")
        return thread

    @staticmethod
    def _upstream_metadata_from_thread(thread: RoadmapChatThread) -> dict[str, object]:
        """
        根据本地线程记录构造上游 Deer-Flow metadata。

        Args:
            thread: 本地线程。

        Returns:
            metadata 字典。

        Raises:
            None
        """

        if thread.roadmap_id is None:
            return {
                "user_id": thread.user_id,
                "source": "deerflow_standalone",
            }
        return {
            "user_id": thread.user_id,
            "roadmap_id": thread.roadmap_id,
            "stage_id": thread.stage_id,
            "task_id": thread.task_id,
            "concept_id": thread.concept_id,
            "source": "roadmap_agent",
        }

    async def _ensure_upstream_thread_exists(self, thread: RoadmapChatThread) -> None:
        """
        确保 Deer-Flow 上游线程存在。

        Args:
            thread: 本地线程记录。

        Returns:
            None

        Raises:
            ExternalServiceError: 上游创建线程失败。
        """

        await self._create_upstream_thread(
            thread_id=thread.thread_id,
            metadata=self._upstream_metadata_from_thread(thread),
        )

    async def _create_upstream_thread(
        self,
        *,
        thread_id: str,
        metadata: dict[str, object],
    ) -> None:
        """
        在 Deer-Flow 上游创建线程。

        Args:
            thread_id: 线程 ID。
            metadata: 线程元数据。

        Returns:
            None

        Raises:
            ExternalServiceError: 上游创建失败。
            TimeoutError: 上游请求超时。
        """

        client = self._build_http_client(streaming=False)
        try:
            response = await client.post(
                "/api/threads",
                headers=self._build_upstream_headers(),
                json={
                    "thread_id": thread_id,
                    "metadata": metadata,
                },
            )
            if response.status_code >= 400:
                raise errors.ExternalServiceError(msg=self._extract_error_message(response))
        except httpx.TimeoutException as exc:
            raise errors.TimeoutError(msg="Deer-Flow 创建线程超时") from exc
        except httpx.HTTPError as exc:
            raise errors.ExternalServiceError(msg="Deer-Flow 创建线程失败") from exc
        finally:
            await client.aclose()

    async def _delete_upstream_thread(self, thread_id: str) -> None:
        """
        删除 Deer-Flow 上游线程。

        Args:
            thread_id: 线程 ID。

        Returns:
            None

        Raises:
            ExternalServiceError: 上游删除失败。
        """

        client = self._build_http_client(streaming=False)
        try:
            response = await client.delete(
                f"/api/threads/{thread_id}",
                headers=self._build_upstream_headers(),
            )
            if response.status_code >= 400:
                raise errors.ExternalServiceError(msg=self._extract_error_message(response))
        except httpx.TimeoutException as exc:
            raise errors.TimeoutError(msg="Deer-Flow 删除线程超时") from exc
        except httpx.HTTPError as exc:
            raise errors.ExternalServiceError(msg="Deer-Flow 删除线程失败") from exc
        finally:
            await client.aclose()

    async def _fetch_upstream_thread_state(self, thread_id: str) -> dict[str, Any]:
        """
        获取 Deer-Flow 线程状态快照。

        Args:
            thread_id: 线程 ID。

        Returns:
            线程状态字典。

        Raises:
            ExternalServiceError: 上游查询失败。
        """

        client = self._build_http_client(streaming=False)
        try:
            response = await client.get(
                f"/api/threads/{thread_id}/state",
                headers=self._build_upstream_headers(),
            )
            if response.status_code >= 400:
                raise errors.ExternalServiceError(msg=self._extract_error_message(response))
            return response.json()
        except httpx.TimeoutException as exc:
            raise errors.TimeoutError(msg="Deer-Flow 获取线程状态超时") from exc
        except httpx.HTTPError as exc:
            raise errors.ExternalServiceError(msg="Deer-Flow 获取线程状态失败") from exc
        finally:
            await client.aclose()

    async def _sync_thread_after_stream(
        self,
        *,
        thread_id: str,
        fallback_title: str,
        fallback_model_id: str | None,
        fallback_assistant_id: str | None,
    ) -> None:
        """
        在流结束后把上游状态回写到本地线程映射。

        Args:
            thread_id: 线程 ID。
            fallback_title: 回退标题。
            fallback_model_id: 回退模型 ID。
            fallback_assistant_id: 回退 assistant ID。

        Returns:
            None

        Raises:
            None
        """

        try:
            state = await self._fetch_upstream_thread_state(thread_id)
            upstream_messages = state.get("values", {}).get("messages", [])
            if not isinstance(upstream_messages, list):
                upstream_messages = []

            visible_messages = self._map_upstream_messages_to_responses(
                thread=None,
                upstream_messages=upstream_messages,
            )
            upstream_artifacts = state.get("values", {}).get("artifacts", [])
            normalized_artifacts = (
                [str(item) for item in upstream_artifacts if isinstance(item, str)]
                if isinstance(upstream_artifacts, list)
                else []
            )
            last_message_preview = None
            last_message_at = None
            if visible_messages:
                last_visible_message = visible_messages[-1]
                last_message_preview = last_visible_message.content[:160]
                last_message_at = last_visible_message.created_at

            title = state.get("values", {}).get("title") or fallback_title
            status = "idle"
            if state.get("tasks"):
                status = "interrupted"

            async with async_session_maker.begin() as session:
                await self.roadmap_chat_thread_crud.update_thread_state(
                    session,
                    thread_id=thread_id,
                    title=str(title)[:200] if title else fallback_title,
                    assistant_id=fallback_assistant_id,
                    model_id=fallback_model_id,
                    message_count=len(visible_messages),
                    last_message_preview=last_message_preview,
                    last_message_at=last_message_at,
                    metadata_json={
                        "status": status,
                        "artifacts": normalized_artifacts,
                    },
                )
        except Exception as exc:
            logger.warning(
                "deerflow_thread_sync_failed",
                thread_id=thread_id,
                error=str(exc),
            )

    async def _get_owned_thread(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        thread_id: str,
    ) -> RoadmapChatThread:
        """
        获取属于当前用户的线程。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            thread_id: 线程 ID。

        Returns:
            线程记录。

        Raises:
            NotFoundError: 线程不存在或不属于当前用户。
        """

        thread = await self.roadmap_chat_thread_crud.get_by_thread_id(
            db,
            thread_id=thread_id,
        )
        if thread is None or thread.user_id != user_id:
            raise errors.NotFoundError(msg="线程不存在")
        return thread

    def _serialize_thread(self, thread: RoadmapChatThread) -> DeerFlowMentorThreadResponse:
        """
        序列化线程响应。

        Args:
            thread: 线程记录。

        Returns:
            线程响应对象。

        Raises:
            None
        """

        metadata = dict(thread.metadata_json or {})
        status = str(metadata.get("status") or "idle")
        return DeerFlowMentorThreadResponse(
            thread_id=thread.thread_id,
            user_id=thread.user_id,
            roadmap_id=thread.roadmap_id,
            stage_id=thread.stage_id,
            task_id=thread.task_id,
            concept_id=thread.concept_id,
            title=thread.title,
            source="deer_flow",
            assistant_id=thread.assistant_id,
            model_id=thread.model_id,
            status=status,
            message_count=thread.message_count,
            last_message_preview=thread.last_message_preview,
            last_message_at=thread.last_message_at,
            metadata=metadata,
            created_at=thread.created_at,
            updated_at=thread.updated_at,
        )

    def _build_http_client(self, *, streaming: bool) -> httpx.AsyncClient:
        """
        构建 Deer-Flow HTTP 客户端。

        Args:
            streaming: 是否用于流式请求。

        Returns:
            AsyncClient 实例。

        Raises:
            ExternalServiceError: 配置缺失时抛出。
        """

        base_url = (settings.DEERFLOW_BASE_URL or "").rstrip("/")
        if not base_url:
            raise errors.ExternalServiceError(msg="未配置 DEERFLOW_BASE_URL")

        timeout = httpx.Timeout(
            connect=settings.DEERFLOW_STREAM_CONNECT_TIMEOUT_SECONDS if streaming else settings.DEERFLOW_REQUEST_TIMEOUT_SECONDS,
            read=settings.DEERFLOW_STREAM_READ_TIMEOUT_SECONDS if streaming else settings.DEERFLOW_REQUEST_TIMEOUT_SECONDS,
            write=settings.DEERFLOW_REQUEST_TIMEOUT_SECONDS,
            pool=settings.DEERFLOW_REQUEST_TIMEOUT_SECONDS,
        )
        return httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            follow_redirects=True,
        )

    def _build_upstream_headers(self) -> dict[str, str]:
        """
        构建 Deer-Flow 上游请求头。

        Args:
            None

        Returns:
            请求头字典。

        Raises:
            None
        """

        headers = {
            "Content-Type": "application/json",
        }
        if settings.DEERFLOW_API_KEY:
            headers["Authorization"] = f"Bearer {settings.DEERFLOW_API_KEY}"
        return headers

    @staticmethod
    async def _read_upstream_error(response: httpx.Response) -> str:
        """
        读取上游错误响应。

        Args:
            response: 上游响应对象。

        Returns:
            可读错误消息。

        Raises:
            None
        """

        try:
            payload = await response.aread()
            if not payload:
                return f"Deer-Flow 请求失败（HTTP {response.status_code}）"
            text = payload.decode("utf-8", errors="ignore")
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                return text

            if isinstance(data, dict):
                return str(data.get("detail") or data.get("message") or text)
            return text
        except Exception:
            return f"Deer-Flow 请求失败（HTTP {response.status_code}）"

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        """
        从普通 HTTP 响应中提取错误消息。

        Args:
            response: HTTP 响应。

        Returns:
            错误消息。

        Raises:
            None
        """

        try:
            data = response.json()
        except Exception:
            return response.text or f"Deer-Flow 请求失败（HTTP {response.status_code}）"

        if isinstance(data, dict):
            return str(data.get("detail") or data.get("message") or response.text)
        return response.text or f"Deer-Flow 请求失败（HTTP {response.status_code}）"

    def _map_upstream_messages_to_responses(
        self,
        *,
        thread: RoadmapChatThread | None,
        upstream_messages: list[dict[str, Any]],
    ) -> list[DeerFlowMentorMessageResponse]:
        """
        将 Deer-Flow state.messages 转为前端消息 DTO。

        Args:
            thread: 本地线程记录。
            upstream_messages: 上游消息列表。

        Returns:
            规范化后的消息列表。

        Raises:
            None
        """

        base_time = thread.created_at if thread is not None else beijing_now()
        messages: list[DeerFlowMentorMessageResponse] = []

        tool_results = self._collect_tool_results(upstream_messages)

        for index, item in enumerate(upstream_messages):
            message_type = str(item.get("type") or "")
            if message_type not in {"human", "ai"}:
                continue

            role = "user" if message_type == "human" else "assistant"
            content = self._extract_message_text(item.get("content"))
            if role == "user":
                content = self.context_service.strip_injected_context(content)

            message_metadata = self._build_message_metadata(
                item,
                role=role,
                tool_results=tool_results,
            )
            if not content and not message_metadata:
                continue

            created_at = base_time + timedelta(seconds=index)
            thread_id = thread.thread_id if thread is not None else ""
            message_id = str(item.get("id") or f"{thread_id}-msg-{index}")
            messages.append(
                DeerFlowMentorMessageResponse(
                    message_id=message_id,
                    thread_id=thread_id,
                    role=role,
                    content=content,
                    message_metadata=message_metadata,
                    created_at=created_at,
                )
            )

        return messages

    @staticmethod
    def _coerce_tool_invocation_arguments(tool_call: dict[str, Any]) -> dict[str, Any]:
        """
        将上游 tool_call 参数统一为 dict，供前端展示 path/query 等字段。

        LangGraph / OpenAI 序列化可能使用 args dict、arguments JSON 字符串或 function.arguments。
        """

        raw_args = tool_call.get("args")
        if isinstance(raw_args, dict):
            return dict(raw_args)
        if isinstance(raw_args, str) and raw_args.strip():
            try:
                parsed = json.loads(raw_args)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                return parsed

        raw_arguments = tool_call.get("arguments")
        if isinstance(raw_arguments, dict):
            return dict(raw_arguments)
        if isinstance(raw_arguments, str) and raw_arguments.strip():
            try:
                parsed = json.loads(raw_arguments)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                return parsed

        func = tool_call.get("function")
        if isinstance(func, dict):
            fn_args = func.get("arguments")
            if isinstance(fn_args, dict):
                return dict(fn_args)
            if isinstance(fn_args, str) and fn_args.strip():
                try:
                    parsed = json.loads(fn_args)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, dict):
                    return parsed

        return {}

    @staticmethod
    def _build_message_metadata(
        item: dict[str, Any],
        *,
        role: str,
        tool_results: dict[str, dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        为前端构建消息扩展元数据。

        Args:
            item: 上游消息对象。
            role: 归一化后的消息角色。

        Returns:
            适合前端渲染的元数据；无额外信息时返回 None。

        Raises:
            None
        """

        if role != "assistant":
            return None

        content_parts: list[dict[str, Any]] = []
        reasoning_content = (
            item.get("additional_kwargs", {}) or {}
        ).get("reasoning_content")
        if isinstance(reasoning_content, str) and reasoning_content.strip():
            content_parts.append(
                {
                    "type": "thinking",
                    "text": reasoning_content.strip(),
                }
            )

        text_content = DeerFlowProxyService._extract_message_text(item.get("content"))
        if isinstance(text_content, str) and text_content.strip():
            content_parts.append(
                {
                    "type": "text",
                    "text": text_content.strip(),
                }
            )

        for tool_call in item.get("tool_calls") or []:
            if not isinstance(tool_call, dict):
                continue

            tool_call_id = tool_call.get("id")
            tool_name = tool_call.get("name")
            if not isinstance(tool_name, str) or not tool_name.strip():
                continue

            result_payload = tool_results.get(str(tool_call_id or ""))
            result_text = None
            is_error = False
            if result_payload:
                result_text = result_payload.get("result")
                is_error = result_payload.get("is_error", False) is True

            content_parts.append(
                {
                    "type": "tool-call",
                    "toolCallId": str(tool_call_id or ""),
                    "toolName": tool_name.strip(),
                    "arguments": DeerFlowProxyService._coerce_tool_invocation_arguments(tool_call),
                    "state": "completed" if result_text else "running",
                    "result": result_text,
                    "isError": is_error,
                }
            )

        if not content_parts:
            return None

        return {
            "content_parts": content_parts,
            "contentParts": content_parts,
        }

    @staticmethod
    def _collect_tool_results(upstream_messages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        """
        收集 tool message 结果，供 assistant 消息元数据补全。

        Args:
            upstream_messages: 上游消息列表。

        Returns:
            tool_call_id 到执行结果的映射。

        Raises:
            None
        """

        results: dict[str, dict[str, Any]] = {}
        for item in upstream_messages:
            if str(item.get("type") or "") != "tool":
                continue

            tool_call_id = item.get("tool_call_id")
            if not isinstance(tool_call_id, str) or not tool_call_id.strip():
                continue

            results[tool_call_id] = {
                "result": DeerFlowProxyService._extract_message_text(item.get("content")),
                "is_error": str(item.get("status") or "").lower() == "error",
            }

        return results

    @staticmethod
    def _extract_message_text(content: Any) -> str:
        """
        从 Deer-Flow 消息内容中提取可展示纯文本。

        Args:
            content: 原始 content 字段。

        Returns:
            纯文本内容。

        Raises:
            None
        """

        if isinstance(content, str):
            return content.strip()

        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                    continue

                if isinstance(part, dict):
                    text_value = part.get("text")
                    if isinstance(text_value, str):
                        text_parts.append(text_value)
            return "\n".join(text_parts).strip()

        return str(content or "").strip()


_deerflow_proxy_service: DeerFlowProxyService | None = None


def get_deerflow_proxy_service() -> DeerFlowProxyService:
    """
    获取 Deer-Flow 代理服务单例。

    Args:
        None

    Returns:
        DeerFlowProxyService 实例。

    Raises:
        None
    """

    global _deerflow_proxy_service
    if _deerflow_proxy_service is None:
        _deerflow_proxy_service = DeerFlowProxyService()
    return _deerflow_proxy_service
