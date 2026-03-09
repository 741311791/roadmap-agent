"""
Mentor 聊天服务。
"""
from __future__ import annotations

from typing import Any, AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.mentor_agent import MentorAgent
from app.config.settings import Settings, settings
from app.crud.crud_chat import chat_message_crud, chat_session_crud
from app.crud.crud_roadmap import get_roadmap_crud
from app.crud.crud_tech_assessment import get_user_profile_crud
from app.db.session import async_session_maker
from app.models.database import beijing_now
from app.schemas.mentor import (
    MentorAgentMode,
    MentorHistoryMessageResponse,
    MentorMessageInput,
    MentorSessionSummaryResponse,
)

logger = structlog.get_logger(__name__)


class MentorService:
    """
    Mentor 聊天业务服务。

    Args:
        app_settings: 全局配置对象。

    Returns:
        无。

    Raises:
        无。
    """

    def __init__(self, app_settings: Settings):
        """
        初始化 MentorService。

        Args:
            app_settings: 全局配置对象。
        """
        self.settings = app_settings
        self.mentor_agent = MentorAgent(app_settings)
        self.roadmap_crud = get_roadmap_crud()
        self.user_profile_crud = get_user_profile_crud()

    def _find_concept_name(self, framework_data: dict[str, Any], concept_id: str | None) -> str | None:
        """
        从路线图框架中查找概念名称。

        Args:
            framework_data: 路线图框架数据。
            concept_id: 概念 ID。

        Returns:
            概念名称，不存在时返回 None。
        """
        if not concept_id:
            return None

        stages = framework_data.get("stages", [])
        for stage in stages:
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    if concept.get("concept_id") == concept_id:
                        return concept.get("name") or concept_id
        return None

    async def _ensure_roadmap_access(
        self,
        db: AsyncSession,
        user_id: str,
        roadmap_id: str,
    ) -> Any:
        """
        校验用户对路线图的访问权限。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            roadmap_id: 路线图 ID。

        Returns:
            路线图实体对象。

        Raises:
            ValueError: 路线图不存在。
            PermissionError: 用户无权访问。
        """
        roadmap = await self.roadmap_crud.get_by_roadmap_id(db, roadmap_id)
        if not roadmap:
            raise ValueError("路线图不存在")
        if roadmap.user_id != user_id:
            raise PermissionError("无权限访问该路线图")
        return roadmap

    async def _build_context(
        self,
        db: AsyncSession,
        user_id: str,
        roadmap_id: str,
        concept_id: str | None,
    ) -> dict[str, Any]:
        """
        构建 Mentor 对话上下文。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            roadmap_id: 路线图 ID。
            concept_id: 当前概念 ID。

        Returns:
            供 Agent 使用的上下文。
        """
        roadmap = await self._ensure_roadmap_access(db=db, user_id=user_id, roadmap_id=roadmap_id)
        profile = await self.user_profile_crud.get_by_user_id(db, user_id)
        concept_name = self._find_concept_name(roadmap.framework_data or {}, concept_id)
        user_background = None
        if profile:
            user_background = profile.current_role or profile.industry
        return {
            "roadmap_title": roadmap.title,
            "current_concept": concept_name,
            "user_background": user_background,
        }

    def _extract_latest_user_message(self, messages: list[MentorMessageInput]) -> str:
        """
        提取本次请求中的最后一条用户消息。

        Args:
            messages: 请求消息列表。

        Returns:
            最后一条用户消息文本。

        Raises:
            ValueError: 没有有效用户消息。
        """
        for message in reversed(messages):
            if message.role == "user" and message.content.strip():
                return message.content.strip()
        raise ValueError("请求中缺少有效的用户消息")

    async def _resolve_session(
        self,
        user_id: str,
        roadmap_id: str,
        concept_id: str | None,
        agent_mode: MentorAgentMode,
        session_id: str | None,
    ) -> str:
        """
        解析或创建会话。

        Args:
            user_id: 用户 ID。
            roadmap_id: 路线图 ID。
            concept_id: 概念 ID。
            agent_mode: 会话模式。
            session_id: 客户端传入的会话 ID。

        Returns:
            会话 ID。

        Raises:
            ValueError: 会话不存在。
            PermissionError: 会话不属于当前用户或模式不匹配。
        """
        async with async_session_maker.begin() as session:
            if session_id:
                chat_session = await chat_session_crud.get_by_id(session, session_id)
                if not chat_session:
                    raise ValueError("会话不存在")
                if chat_session.user_id != user_id or chat_session.roadmap_id != roadmap_id:
                    raise PermissionError("无权限访问该会话")
                if chat_session.agent_mode != agent_mode:
                    raise PermissionError("会话模式不匹配")

                if concept_id and chat_session.concept_id != concept_id:
                    chat_session.concept_id = concept_id
                    chat_session.updated_at = beijing_now()
                    await session.flush()
                return chat_session.session_id

            chat_session = await chat_session_crud.create(
                session,
                obj_in={
                    "user_id": user_id,
                    "roadmap_id": roadmap_id,
                    "concept_id": concept_id,
                    "agent_mode": agent_mode,
                },
            )
            return chat_session.session_id

    async def _append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        message_metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        追加一条聊天消息。

        Args:
            session_id: 会话 ID。
            role: 消息角色。
            content: 消息内容。
            message_metadata: 消息元数据。

        Returns:
            新消息 ID。
        """
        async with async_session_maker.begin() as session:
            message = await chat_message_crud.create(
                session,
                obj_in={
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "message_metadata": message_metadata,
                },
            )
            return message.message_id

    async def _update_session_metadata(self, session_id: str, last_message_preview: str) -> None:
        """
        同步会话统计信息。

        Args:
            session_id: 会话 ID。
            last_message_preview: 最后一条消息预览。
        """
        async with async_session_maker.begin() as session:
            message_count = await chat_message_crud.count_by_session(session, session_id)
            await chat_session_crud.update_metadata(
                session=session,
                session_id=session_id,
                message_count=message_count,
                last_message_preview=last_message_preview[:200],
            )

    async def _load_agent_history(self, session_id: str) -> list[dict[str, str]]:
        """
        加载给 Agent 使用的历史消息。

        Args:
            session_id: 会话 ID。

        Returns:
            Agent 输入消息列表。
        """
        max_messages = max(self.settings.MENTOR_MAX_CONTEXT_MESSAGES, 1)
        async with async_session_maker() as session:
            history_messages = await chat_message_crud.get_recent_messages(
                session=session,
                session_id=session_id,
                limit=max_messages,
            )

        agent_messages: list[dict[str, str]] = []
        for history_message in history_messages:
            if history_message.role not in {"user", "assistant"}:
                continue
            if not history_message.content.strip():
                continue
            agent_messages.append(
                {
                    "role": history_message.role,
                    "content": history_message.content,
                }
            )
        return agent_messages

    async def list_sessions(
        self,
        db: AsyncSession,
        user_id: str,
        roadmap_id: str,
        agent_mode: MentorAgentMode | None = None,
        limit: int = 20,
    ) -> list[MentorSessionSummaryResponse]:
        """
        获取用户在路线图下的聊天会话列表。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            roadmap_id: 路线图 ID。
            agent_mode: 会话模式过滤。
            limit: 返回数量上限。

        Returns:
            会话摘要列表。
        """
        await self._ensure_roadmap_access(db=db, user_id=user_id, roadmap_id=roadmap_id)
        sessions = await chat_session_crud.get_user_sessions(
            session=db,
            user_id=user_id,
            roadmap_id=roadmap_id,
            agent_mode=agent_mode,
            limit=max(limit, 1),
            offset=0,
        )
        return [
            MentorSessionSummaryResponse(
                session_id=item.session_id,
                roadmap_id=item.roadmap_id,
                concept_id=item.concept_id,
                agent_mode=item.agent_mode,  # type: ignore[arg-type]
                title=item.title,
                message_count=item.message_count,
                last_message_preview=item.last_message_preview,
                updated_at=item.updated_at,
            )
            for item in sessions
        ]

    async def get_session_messages(
        self,
        db: AsyncSession,
        user_id: str,
        roadmap_id: str,
        session_id: str,
        limit: int = 200,
    ) -> list[MentorHistoryMessageResponse]:
        """
        获取指定会话的消息历史。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            roadmap_id: 路线图 ID。
            session_id: 会话 ID。
            limit: 返回数量上限。

        Returns:
            历史消息列表。
        """
        await self._ensure_roadmap_access(db=db, user_id=user_id, roadmap_id=roadmap_id)
        chat_session = await chat_session_crud.get_by_id(db, session_id)
        if not chat_session:
            raise ValueError("会话不存在")
        if chat_session.user_id != user_id or chat_session.roadmap_id != roadmap_id:
            raise PermissionError("无权限访问该会话")

        history = await chat_message_crud.get_by_session(
            session=db,
            session_id=session_id,
            limit=max(limit, 1),
            offset=0,
        )
        return [
            MentorHistoryMessageResponse(
                message_id=item.message_id,
                role=item.role,  # type: ignore[arg-type]
                content=item.content,
                message_metadata=item.message_metadata,
                created_at=item.created_at,
            )
            for item in history
        ]

    async def stream_chat(
        self,
        db: AsyncSession,
        user_id: str,
        roadmap_id: str,
        messages: list[MentorMessageInput],
        agent_mode: MentorAgentMode,
        concept_id: str | None,
        session_id: str | None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        以 SSE 事件格式流式返回 Mentor 对话结果，并持久化会话历史。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            roadmap_id: 路线图 ID。
            messages: 请求消息列表。
            agent_mode: Agent 模式。
            concept_id: 当前概念 ID。
            session_id: 会话 ID（可选）。

        Returns:
            SSE 事件字典流。
        """
        try:
            context = await self._build_context(
                db=db,
                user_id=user_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
            active_session_id = await self._resolve_session(
                user_id=user_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                agent_mode=agent_mode,
                session_id=session_id,
            )
            user_text = self._extract_latest_user_message(messages)

            await self._append_message(
                session_id=active_session_id,
                role="user",
                content=user_text,
                message_metadata={
                    "agent_mode": agent_mode,
                    "concept_id": concept_id,
                },
            )
            await self._update_session_metadata(active_session_id, user_text)

            history_messages = await self._load_agent_history(active_session_id)
            assistant_chunks: list[str] = []
            tool_call_state: dict[str, dict[str, Any]] = {}

            async for event in self.mentor_agent.stream_chat(
                messages=history_messages,
                agent_mode=agent_mode,
                user_id=user_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                roadmap_title=context["roadmap_title"],
                current_concept=context["current_concept"],
                user_background=context["user_background"],
            ):
                if event.get("type") == "text_delta":
                    content = str(event.get("content", ""))
                    if content:
                        assistant_chunks.append(content)
                elif event.get("type") == "tool_call_start":
                    tool_call_id = str(event.get("tool_call_id", ""))
                    if tool_call_id:
                        tool_call_state[tool_call_id] = {
                            "tool_call_id": tool_call_id,
                            "tool_name": event.get("tool_name"),
                            "args": event.get("args"),
                            "loading": True,
                        }
                elif event.get("type") == "tool_call_end":
                    tool_call_id = str(event.get("tool_call_id", ""))
                    if tool_call_id:
                        current_state = tool_call_state.get(
                            tool_call_id,
                            {
                                "tool_call_id": tool_call_id,
                                "tool_name": event.get("tool_name"),
                            },
                        )
                        current_state.update(
                            {
                                "loading": False,
                                "success": event.get("success", True),
                                "result": event.get("result"),
                            }
                        )
                        tool_call_state[tool_call_id] = current_state
                yield event

            assistant_text = "".join(assistant_chunks).strip()
            assistant_message_id = await self._append_message(
                session_id=active_session_id,
                role="assistant",
                content=assistant_text or "（无文本输出）",
                message_metadata={
                    "agent_mode": agent_mode,
                    "concept_id": concept_id,
                    "tool_calls": list(tool_call_state.values()),
                },
            )
            await self._update_session_metadata(
                active_session_id,
                assistant_text or "（无文本输出）",
            )

            yield {
                "type": "done",
                "message_id": assistant_message_id,
                "session_id": active_session_id,
            }

        except PermissionError as exc:
            logger.warning(
                "mentor_chat_permission_denied",
                user_id=user_id,
                roadmap_id=roadmap_id,
                error=str(exc),
            )
            yield {
                "type": "error",
                "message": "无权限访问该路线图",
            }
        except ValueError as exc:
            logger.warning(
                "mentor_chat_invalid_request",
                user_id=user_id,
                roadmap_id=roadmap_id,
                error=str(exc),
            )
            yield {
                "type": "error",
                "message": str(exc),
            }
        except Exception as exc:  # pragma: no cover
            logger.exception(
                "mentor_chat_stream_failed",
                user_id=user_id,
                roadmap_id=roadmap_id,
                error=str(exc),
            )
            yield {
                "type": "error",
                "message": "Mentor 服务暂时不可用，请稍后再试",
            }


def get_mentor_service() -> MentorService:
    """
    获取 MentorService 实例。

    Returns:
        MentorService: 服务实例。
    """
    return MentorService(settings)

