"""
Deer-Flow 上下文编排服务
"""
from __future__ import annotations

from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.custom_exceptions import errors
from app.crud.crud_roadmap import RoadmapCRUD, get_roadmap_crud
from app.models.database import RoadmapMetadata, User
from app.schemas.deerflow_standalone import (
    DeerFlowStandaloneChatRequest,
    DeerFlowStandaloneThreadCreateRequest,
)
from app.schemas.mentor_deerflow import (
    DeerFlowMentorChatRequest,
    DeerFlowMentorThreadCreateRequest,
    DeerFlowReasoningEffort,
    DeerFlowRuntimeMode,
)
from app.services.learning.mentor_context_service import (
    MentorContextService,
    get_mentor_context_service,
)

logger = structlog.get_logger()

_CONTEXT_OPEN_TAG = "<learning_context>"
_CONTEXT_CLOSE_TAG = "</learning_context>"
_REQUEST_OPEN_TAG = "<user_request>"
_REQUEST_CLOSE_TAG = "</user_request>"


@dataclass(slots=True)
class DeerFlowPreparedChatPayload:
    """
    Deer-Flow 聊天预处理结果

    Args:
        upstream_message: 发送给 Deer-Flow 的用户消息
        title: 线程标题建议
        model_id: 当前模型 ID
        model_name: 解析后的模型名称
        assistant_id: Deer-Flow assistant ID
        metadata: 线程元数据
        runtime_context: Deer-Flow 运行时上下文
        preview_text: 供本地线程列表展示的原始用户消息

    Returns:
        None

    Raises:
        None
    """

    upstream_message: str
    title: str
    model_id: str | None
    model_name: str | None
    assistant_id: str
    metadata: dict[str, object]
    runtime_context: dict[str, object]
    preview_text: str


class DeerFlowContextService:
    """
    负责为 Deer-Flow 代理链路构建业务上下文。
    """

    def __init__(
        self,
        roadmap_crud: RoadmapCRUD | None = None,
        mentor_context_service: MentorContextService | None = None,
    ) -> None:
        """
        初始化上下文服务。

        Args:
            roadmap_crud: 路线图 CRUD。
            mentor_context_service: 现有 Mentor 上下文服务。

        Returns:
            None

        Raises:
            None
        """

        self.roadmap_crud = roadmap_crud or get_roadmap_crud()
        self.mentor_context_service = mentor_context_service or get_mentor_context_service()

    async def ensure_roadmap_access(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        roadmap_id: str,
    ) -> RoadmapMetadata:
        """
        校验路线图访问权限并返回路线图。

        Args:
            db: 数据库会话。
            user_id: 当前用户 ID。
            roadmap_id: 路线图 ID。

        Returns:
            路线图对象。

        Raises:
            NotFoundError: 路线图不存在。
            ForbiddenError: 当前用户无权访问路线图。
        """

        roadmap = await self.roadmap_crud.get_by_roadmap_id(db, roadmap_id)
        if roadmap is None:
            raise errors.NotFoundError(msg="路线图不存在")

        if roadmap.user_id != user_id and roadmap.user_id != settings.FEATURED_USER_ID:
            raise errors.ForbiddenError(msg="无权访问该路线图")

        return roadmap

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
        预热 Deer-Flow 代理所需上下文缓存。

        Args:
            db: 数据库会话。
            user_id: 当前用户 ID。
            roadmap_id: 路线图 ID。
            concept_id: 当前概念 ID。
            concept_title: 当前概念标题。

        Returns:
            预热结果摘要。

        Raises:
            NotFoundError: 路线图不存在。
            ForbiddenError: 当前用户无权访问路线图。
        """

        await self.ensure_roadmap_access(
            db,
            user_id=user_id,
            roadmap_id=roadmap_id,
        )
        return await self.mentor_context_service.warmup_context_cache(
            db,
            user_id=user_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            concept_title=concept_title,
        )

    async def prepare_chat_payload(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        request: DeerFlowMentorChatRequest,
    ) -> DeerFlowPreparedChatPayload:
        """
        构建 Deer-Flow 运行所需上下文。

        Args:
            db: 数据库会话。
            current_user: 当前用户。
            request: 聊天请求。

        Returns:
            预处理后的 Deer-Flow 聊天载荷。

        Raises:
            RequestError: 用户消息为空。
            NotFoundError: 路线图不存在。
            ForbiddenError: 当前用户无权访问路线图。
        """

        user_message = request.message.strip()
        if not user_message:
            raise errors.RequestError(msg="消息不能为空")

        roadmap = await self.ensure_roadmap_access(
            db,
            user_id=current_user.id,
            roadmap_id=request.context.roadmap_id,
        )
        learning_context = await self.mentor_context_service.get_learning_context_from_roadmap_cached(
            db,
            roadmap=roadmap,
            roadmap_id=request.context.roadmap_id,
            concept_id=request.context.concept_id,
        )

        if request.context.concept_title:
            learning_context["concept_title"] = request.context.concept_title
        if request.context.tutorial_excerpt:
            learning_context["tutorial_excerpt"] = request.context.tutorial_excerpt[
                : settings.MENTOR_CONTEXT_EXCERPT_MAX_LENGTH
            ]
        if request.context.roadmap_context:
            learning_context["roadmap_context"] = request.context.roadmap_context

        ltm_facts = await self.mentor_context_service.get_long_term_memories_cached(
            user_id=current_user.id,
            message=user_message,
            roadmap_id=request.context.roadmap_id,
            concept_id=request.context.concept_id,
        )
        ltm_sections = self.mentor_context_service.build_long_term_memory_sections(ltm_facts)

        model_name: str | None = request.model_id.strip() if request.model_id else settings.DEERFLOW_DEFAULT_MODEL_NAME
        resolved_model_id = model_name

        title = (
            request.context.concept_title
            or learning_context.get("concept_title")
            or user_message[:20]
        )
        assistant_id = (request.assistant_id or settings.DEERFLOW_DEFAULT_ASSISTANT_ID).strip()
        if not assistant_id:
            assistant_id = "lead_agent"

        upstream_message = self._build_contextualized_user_message(
            current_user=current_user,
            roadmap=roadmap,
            request=request,
            learning_context=learning_context,
            ltm_sections=ltm_sections,
            user_message=user_message,
        )
        metadata = {
            "user_id": current_user.id,
            "roadmap_id": request.context.roadmap_id,
            "stage_id": request.context.stage_id,
            "task_id": request.context.task_id,
            "concept_id": request.context.concept_id,
            "source": "roadmap_agent",
        }
        runtime_context = self.build_runtime_context(
            model_name=model_name,
            mode=request.context.mode,
            reasoning_effort=request.context.reasoning_effort,
        )

        return DeerFlowPreparedChatPayload(
            upstream_message=upstream_message,
            title=str(title)[:200],
            model_id=resolved_model_id,
            model_name=model_name,
            assistant_id=assistant_id,
            metadata=metadata,
            runtime_context=runtime_context,
            preview_text=user_message,
        )

    async def prepare_thread_create_context(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        request: DeerFlowMentorThreadCreateRequest,
    ) -> tuple[RoadmapMetadata, str]:
        """
        构建 Deer-Flow 线程创建所需上下文。

        Args:
            db: 数据库会话。
            current_user: 当前用户。
            request: 线程创建请求。

        Returns:
            路线图对象与线程标题。

        Raises:
            NotFoundError: 路线图不存在。
            ForbiddenError: 当前用户无权访问路线图。
        """

        roadmap = await self.ensure_roadmap_access(
            db,
            user_id=current_user.id,
            roadmap_id=request.roadmap_id,
        )
        title = request.title or request.concept_id or roadmap.title
        return roadmap, str(title)[:200]

    async def prepare_standalone_chat_payload(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        request: DeerFlowStandaloneChatRequest,
    ) -> DeerFlowPreparedChatPayload:
        """
        构建独立 Deer-Flow 实验室聊天载荷（不上行学习上下文与 LTM）。

        Args:
            db: 数据库会话（保留签名与伴学一致，便于依赖注入；本方法只读配置）。
            current_user: 当前用户。
            request: 独立聊天请求。

        Returns:
            预处理后的 Deer-Flow 聊天载荷。

        Raises:
            RequestError: 用户消息为空。
        """

        _ = db
        user_message = request.message.strip()
        if not user_message:
            raise errors.RequestError(msg="消息不能为空")

        model_name: str | None = request.model_id.strip() if request.model_id else settings.DEERFLOW_DEFAULT_MODEL_NAME
        resolved_model_id = model_name

        title = user_message[:20]
        assistant_id = (request.assistant_id or settings.DEERFLOW_DEFAULT_ASSISTANT_ID).strip()
        if not assistant_id:
            assistant_id = "lead_agent"

        metadata: dict[str, object] = {
            "user_id": current_user.id,
            "source": "deerflow_standalone",
        }
        runtime_context = self.build_runtime_context(
            model_name=model_name,
            mode=request.context.mode,
            reasoning_effort=request.context.reasoning_effort,
        )

        return DeerFlowPreparedChatPayload(
            upstream_message=user_message,
            title=str(title)[:200],
            model_id=resolved_model_id,
            model_name=model_name,
            assistant_id=assistant_id,
            metadata=metadata,
            runtime_context=runtime_context,
            preview_text=user_message,
        )

    @staticmethod
    def prepare_standalone_thread_title(*, request: DeerFlowStandaloneThreadCreateRequest) -> str:
        """
        独立线程默认标题。

        Args:
            request: 线程创建请求。

        Returns:
            规范化标题。

        Raises:
            None
        """

        raw = (request.title or "New Chat").strip()
        return raw[:200] if raw else "New Chat"

    @staticmethod
    def build_runtime_context(
        *,
        model_name: str | None,
        mode: DeerFlowRuntimeMode | None,
        reasoning_effort: DeerFlowReasoningEffort | None,
    ) -> dict[str, object]:
        """
        与官方 Deer-Flow Web 提交参数对齐（deer-flow/frontend/src/core/threads/hooks.ts）：
        is_plan_mode 为 True 时才挂载 TodoMiddleware / write_todos；Pro / Ultra 对应 is_plan_mode 等。

        Args:
            model_name: 上游模型名。
            mode: 运行模式。
            reasoning_effort: 推理深度。

        Returns:
            供 Gateway 使用的 runtime_context 字典。

        Raises:
            None
        """

        runtime_context: dict[str, object] = {}
        if model_name:
            runtime_context["model_name"] = model_name

        mode_value = mode
        if mode_value:
            runtime_context["mode"] = mode_value
            runtime_context["thinking_enabled"] = mode_value != "flash"

        if reasoning_effort:
            runtime_context["reasoning_effort"] = reasoning_effort
        elif mode_value == "ultra":
            runtime_context["reasoning_effort"] = "high"
        elif mode_value == "pro":
            runtime_context["reasoning_effort"] = "medium"
        elif mode_value == "thinking":
            runtime_context["reasoning_effort"] = "low"

        if mode_value in ("pro", "ultra"):
            runtime_context["is_plan_mode"] = True
        if mode_value == "ultra":
            runtime_context["subagent_enabled"] = True

        return runtime_context

    @staticmethod
    def strip_injected_context(message: str) -> str:
        """
        从持久化的人类消息中剥离注入的学习上下文。

        Args:
            message: Deer-Flow 持久化后的消息内容。

        Returns:
            原始用户输入。

        Raises:
            None
        """

        if _REQUEST_OPEN_TAG not in message or _REQUEST_CLOSE_TAG not in message:
            return message.strip()

        request_segment = message.split(_REQUEST_OPEN_TAG, maxsplit=1)[-1]
        request_segment = request_segment.split(_REQUEST_CLOSE_TAG, maxsplit=1)[0]
        return request_segment.strip()

    def _build_contextualized_user_message(
        self,
        *,
        current_user: User,
        roadmap: RoadmapMetadata,
        request: DeerFlowMentorChatRequest,
        learning_context: dict[str, object],
        ltm_sections: dict[str, list[str]],
        user_message: str,
    ) -> str:
        """
        把主应用上下文包装到 Deer-Flow 用户消息中。

        Args:
            current_user: 当前用户。
            roadmap: 路线图对象。
            request: 聊天请求。
            learning_context: 学习上下文。
            ltm_sections: 长期记忆分组结果。
            user_message: 原始用户输入。

        Returns:
            注入上下文后的消息文本。

        Raises:
            None
        """

        context_lines = [
            "你正在服务于一个学习路线图产品内的路线图详情页聊天场景。",
            f"当前用户 ID：{current_user.id}",
            f"当前路线图标题：{roadmap.title}",
            f"路线图 ID：{request.context.roadmap_id}",
            f"当前阶段 ID：{request.context.stage_id or '无'}",
            f"当前任务 ID：{request.context.task_id or '无'}",
            f"当前概念 ID：{request.context.concept_id or '无'}",
            f"当前概念标题：{learning_context.get('concept_title') or request.context.concept_title or '无'}",
        ]

        roadmap_context = str(learning_context.get("roadmap_context") or "").strip()
        if roadmap_context:
            context_lines.extend(
                [
                    "",
                    "路线图摘要：",
                    roadmap_context,
                ]
            )

        tutorial_excerpt = str(learning_context.get("tutorial_excerpt") or "").strip()
        if tutorial_excerpt:
            context_lines.extend(
                [
                    "",
                    "当前学习材料摘录：",
                    tutorial_excerpt,
                ]
            )

        ltm_blocks = [
            ("用户学习偏好", ltm_sections.get("preferences", [])),
            ("用户当前目标", ltm_sections.get("goals", [])),
            ("用户历史误区", ltm_sections.get("misconceptions", [])),
            ("用户当前进展", ltm_sections.get("progress", [])),
            ("其他长期记忆", ltm_sections.get("other_facts", [])),
        ]
        for title, items in ltm_blocks:
            if not items:
                continue
            context_lines.append("")
            context_lines.append(f"{title}：")
            context_lines.extend(f"- {item}" for item in items)

        context_text = "\n".join(context_lines).strip()
        return (
            f"{_CONTEXT_OPEN_TAG}\n"
            f"{context_text}\n"
            f"{_CONTEXT_CLOSE_TAG}\n\n"
            f"{_REQUEST_OPEN_TAG}\n"
            f"{user_message}\n"
            f"{_REQUEST_CLOSE_TAG}"
        )


_deerflow_context_service: DeerFlowContextService | None = None


def get_deerflow_context_service() -> DeerFlowContextService:
    """
    获取 Deer-Flow 上下文服务单例。

    Args:
        None

    Returns:
        DeerFlowContextService 实例。

    Raises:
        None
    """

    global _deerflow_context_service
    if _deerflow_context_service is None:
        _deerflow_context_service = DeerFlowContextService()
    return _deerflow_context_service
