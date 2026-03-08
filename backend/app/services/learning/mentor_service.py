"""
Mentor 聊天服务。
"""
from __future__ import annotations

from typing import Any, AsyncGenerator
from uuid import uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.mentor_agent import MentorAgent
from app.config.settings import Settings, settings
from app.crud.crud_roadmap import get_roadmap_crud
from app.crud.crud_tech_assessment import get_user_profile_crud
from app.schemas.mentor import MentorAgentMode, MentorMessageInput

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

        Returns:
            无。

        Raises:
            无。
        """

        self.settings = app_settings
        self.mentor_agent = MentorAgent(app_settings)
        self.roadmap_crud = get_roadmap_crud()
        self.user_profile_crud = get_user_profile_crud()

    def _trim_messages(self, messages: list[MentorMessageInput]) -> list[dict[str, str]]:
        """
        裁剪消息历史，避免上下文无限膨胀。

        Args:
            messages: 原始消息列表。

        Returns:
            list[dict[str, str]]: 裁剪后的消息列表。

        Raises:
            无。
        """

        max_messages = self.settings.MENTOR_MAX_CONTEXT_MESSAGES
        trimmed = messages[-max_messages:] if max_messages > 0 else messages
        return [
            {
                "role": msg.role,
                "content": msg.content,
            }
            for msg in trimmed
            if msg.content.strip()
        ]

    def _find_concept_name(self, framework_data: dict[str, Any], concept_id: str | None) -> str | None:
        """
        从路线图框架中查找概念名称。

        Args:
            framework_data: 路线图框架数据。
            concept_id: 概念 ID。

        Returns:
            str | None: 概念名称，不存在时返回 None。

        Raises:
            无。
        """

        if not concept_id:
            return None

        stages = framework_data.get("stages", [])

        # 为什么这样做：框架是嵌套结构，顺序遍历可保证在 MVP 阶段实现最稳妥且可读的定位逻辑。
        for stage in stages:
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    if concept.get("concept_id") == concept_id:
                        return concept.get("name") or concept_id
        return None

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
            dict[str, Any]: 供 Agent 使用的上下文字典。

        Raises:
            ValueError: 当路线图不存在时抛出。
            PermissionError: 当路线图不属于当前用户时抛出。
        """

        roadmap = await self.roadmap_crud.get_by_roadmap_id(db, roadmap_id)
        if not roadmap:
            raise ValueError("路线图不存在")
        if roadmap.user_id != user_id:
            raise PermissionError("无权限访问该路线图")

        profile = await self.user_profile_crud.get_by_user_id(db, user_id)

        concept_name = self._find_concept_name(
            framework_data=roadmap.framework_data or {},
            concept_id=concept_id,
        )
        user_background = None
        if profile:
            user_background = profile.current_role or profile.industry

        return {
            "roadmap_title": roadmap.title,
            "current_concept": concept_name,
            "user_background": user_background,
        }

    async def stream_chat(
        self,
        db: AsyncSession,
        user_id: str,
        roadmap_id: str,
        messages: list[MentorMessageInput],
        agent_mode: MentorAgentMode,
        concept_id: str | None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        以 SSE 事件格式流式返回 Mentor 对话结果。

        Args:
            db: 数据库会话。
            user_id: 用户 ID。
            roadmap_id: 路线图 ID。
            messages: 历史消息。
            agent_mode: Agent 模式。
            concept_id: 当前概念 ID。

        Returns:
            AsyncGenerator[dict[str, Any], None]: SSE 事件字典流。

        Raises:
            无。
        """

        try:
            context = await self._build_context(
                db=db,
                user_id=user_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
            )
            trimmed_messages = self._trim_messages(messages)

            async for event in self.mentor_agent.stream_chat(
                messages=trimmed_messages,
                agent_mode=agent_mode,
                user_id=user_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                roadmap_title=context["roadmap_title"],
                current_concept=context["current_concept"],
                user_background=context["user_background"],
            ):
                yield event

            yield {
                "type": "done",
                "message_id": f"msg_{uuid4().hex}",
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
        except Exception as exc:  # pragma: no cover - 兜底保护
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

    Args:
        无。

    Returns:
        MentorService: 服务实例。

    Raises:
        无。
    """

    return MentorService(settings)

