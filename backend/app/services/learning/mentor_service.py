"""
AI 伴学助手服务
"""
import asyncio
import json
import re
import uuid
from dataclasses import dataclass
from typing import AsyncGenerator, Literal

import structlog
from openai import AuthenticationError, BadRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.factory import AgentFactory, get_agent_factory
from app.agents.mentor_agent import MentorAgentInput
from app.config.settings import settings
from app.core.celery_app import celery_app
from app.core.custom_exceptions import errors
from app.crud.crud_chat import chat_message_crud, chat_session_crud
from app.crud.crud_mentor_memory_job import mentor_memory_job_crud
from app.crud.crud_roadmap import get_roadmap_crud
from app.db.session import async_session_maker
from app.models.database import ChatMessage, ChatSession, MentorMemoryJob, User
from app.schemas.mentor import MentorChatRequest
from app.services.learning.mentor_context_service import (
    MentorContextService,
    get_mentor_context_service,
)
from app.services.learning.mentor_rate_limit_service import (
    MentorRateLimitService,
    get_mentor_rate_limit_service,
)

logger = structlog.get_logger()


@dataclass(slots=True)
class MentorChatStreamContext:
    """
    AI 伴学助手流式上下文
    """

    session_id: str
    trace_id: str
    user_message_id: str
    assistant_message_id: str
    stream: AsyncGenerator[str, None]


class MentorService:
    """
    AI 伴学助手服务
    """

    STREAM_SANITIZE_HOLDBACK_CHARS = 24
    MARKDOWN_HORIZONTAL_RULE_PATTERN = re.compile(r"(?m)^[ \t]{0,3}(?:---|\*\*\*|___)[ \t]*$")
    INLINE_BOLD_PATTERN = re.compile(r"\*\*[^*\n]+?\*\*")
    INLINE_CODE_PATTERN = re.compile(r"(?<!`)`[^`\n]+`(?!`)")
    INLINE_MARKDOWN_ADJACENT_PATTERN = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")

    def __init__(
        self,
        *,
        agent_factory: AgentFactory | None = None,
        context_service: MentorContextService | None = None,
        rate_limit_service: MentorRateLimitService | None = None,
    ) -> None:
        self.agent_factory = agent_factory or get_agent_factory()
        self.context_service = context_service or get_mentor_context_service()
        self.rate_limit_service = rate_limit_service or get_mentor_rate_limit_service()
        self.roadmap_crud = get_roadmap_crud()
        self.roadmap_crud = get_roadmap_crud()

    async def build_chat_stream(
        self,
        *,
        db: AsyncSession,
        current_user: User,
        request: MentorChatRequest,
        client_ip: str | None,
    ) -> MentorChatStreamContext:
        """
        构建聊天流

        优化说明：
        - 速率限制校验串行前置（保证快速拒绝）
        - 之后将 4 个独立 I/O 通过 asyncio.gather 并行执行：
            1. 路线图权限校验 + 上下文构建（复用单次 roadmap 查询）
            2. 短期记忆读取（Redis）
            3. 长期记忆向量检索（通常最慢，并行后不再阻塞主链路）
            4. 会话初始化（数据库写入）
        """
        await self.rate_limit_service.check_rate_limit(user_id=current_user.id, ip=client_ip)

        session_id = request.session_id or str(uuid.uuid4())
        trace_id = str(uuid.uuid4())
        user_message_id = str(uuid.uuid4())
        assistant_message_id = str(uuid.uuid4())

        # 重要约束：
        # - AsyncSession 不能在多个协程中并发使用。
        # - 因此这里把会访问同一个 db 的步骤串行执行：
        #   1. 路线图权限校验 + context 构建
        #   2. STM 读取（Redis miss 时会回退查 DB）
        # - 与数据库无关的任务仍然保持并行：
        #   3. LTM 缓存 / Mem0 检索
        #   4. 会话初始化（内部自建独立 session）
        ltm_task = asyncio.create_task(
            self.context_service.get_long_term_memories_cached(
                user_id=current_user.id,
                message=request.message,
                roadmap_id=request.context.roadmap_id,
                concept_id=request.context.concept_id,
            )
        )
        ensure_session_task = asyncio.create_task(
            self._ensure_session_exists(
                user_id=current_user.id,
                session_id=session_id,
                request=request,
            )
        )

        learning_context = await self._prepare_context_with_access(
            db,
            current_user=current_user,
            request=request,
        )
        stm_messages = await self.context_service.get_short_term_messages(
            db,
            session_id=session_id,
        )
        ltm_facts, _ = await asyncio.gather(ltm_task, ensure_session_task)

        ltm_fact_summaries = self.context_service.build_long_term_memory_summary(ltm_facts)
        ltm_sections = self.context_service.build_long_term_memory_sections(ltm_facts)
        history_messages = [
            {
                "role": message["role"],
                "content": message["content"],
            }
            for message in stm_messages
            if message.get("role") in {"system", "user", "assistant"}
        ]

        learning_profile = self._build_learning_profile(current_user)
        agent = self.agent_factory.create_mentor_agent(
            agent_type=request.agent_type,
            model_name=request.model_id,
        )
        agent_input = MentorAgentInput(
            user_message=request.message,
            history_messages=history_messages,
            concept_title=learning_context.get("concept_title"),
            tutorial_excerpt=learning_context.get("tutorial_excerpt"),
            roadmap_context=learning_context.get("roadmap_context"),
            ltm_facts=ltm_fact_summaries,
            ltm_preferences=ltm_sections["preferences"],
            ltm_goals=ltm_sections["goals"],
            ltm_misconceptions=ltm_sections["misconceptions"],
            ltm_progress=ltm_sections["progress"],
            ltm_other_facts=ltm_sections["other_facts"],
            learning_profile=learning_profile,
        )

        async def event_stream() -> AsyncGenerator[str, None]:
            """
            SSE 事件流
            """
            raw_assistant_text = ""
            emitted_length = 0
            yield self._build_sse_payload(
                {
                    "type": "meta",
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "user_message_id": user_message_id,
                    "assistant_message_id": assistant_message_id,
                }
            )

            try:
                async for delta in agent.stream_chat(agent_input):
                    raw_assistant_text += delta
                    sanitized_delta, emitted_length = self._build_incremental_sanitized_delta(
                        raw_text=raw_assistant_text,
                        emitted_length=emitted_length,
                    )
                    if sanitized_delta:
                        yield self._build_sse_payload({"type": "delta", "delta": sanitized_delta})
            except Exception as exc:
                logger.exception(
                    "mentor_chat_stream_failed",
                    user_id=current_user.id,
                    session_id=session_id,
                    error=str(exc),
                )
                yield self._build_sse_payload(
                    {
                        "type": "error",
                        "message": self._build_stream_error_message(exc),
                    }
                )
                return

            assistant_message = self._sanitize_assistant_message(raw_assistant_text)
            if not assistant_message:
                assistant_message = "我这次没有成功生成回答，请换一种问法再试试。"
            final_delta = assistant_message[emitted_length:]
            if final_delta:
                yield self._build_sse_payload({"type": "delta", "delta": final_delta})

            try:
                await self._persist_chat_round(
                    current_user=current_user,
                    request=request,
                    session_id=session_id,
                    trace_id=trace_id,
                    user_message_id=user_message_id,
                    assistant_message_id=assistant_message_id,
                    assistant_message=assistant_message,
                )
            except Exception as exc:
                logger.exception(
                    "mentor_chat_persist_failed",
                    user_id=current_user.id,
                    session_id=session_id,
                    trace_id=trace_id,
                    error=str(exc),
                )

            try:
                await self._dispatch_memory_job(
                    current_user=current_user,
                    request=request,
                    session_id=session_id,
                    trace_id=trace_id,
                    user_message_id=user_message_id,
                    assistant_message_id=assistant_message_id,
                    assistant_message=assistant_message,
                )
            except Exception as exc:
                logger.exception(
                    "mentor_memory_job_dispatch_failed",
                    user_id=current_user.id,
                    session_id=session_id,
                    trace_id=trace_id,
                    error=str(exc),
                )
            yield "data: [DONE]\n\n"

        return MentorChatStreamContext(
            session_id=session_id,
            trace_id=trace_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            stream=event_stream(),
        )

    async def warmup_context_cache(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        roadmap_id: str,
        concept_id: str | None,
        concept_title: str | None,
    ) -> dict:
        """
        预热伴学助手 Redis 缓存

        在用户进入路线图详情页或切换章节时异步调用，将以下数据写入 Redis：
        1. 学习上下文（roadmap + tutorial 信息，TTL 30 分钟）
        2. 长期记忆（Mem0 向量检索结果，TTL 10 分钟）

        后续对话直接读取 Redis，彻底避免每次消息触发 Mem0/DB 查询。
        """
        warmup_query = concept_title or roadmap_id
        context_task = self.context_service.warmup_context_cache(
            db,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
        )
        ltm_task = self.context_service.warmup_ltm_cache(
            user_id=user_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
            warmup_query=warmup_query,
        )

        try:
            context, ltm_count = await asyncio.gather(context_task, ltm_task)
            logger.info(
                "mentor_warmup_completed",
                user_id=user_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                ltm_count=ltm_count,
                has_context=bool(context.get("roadmap_context")),
            )
            return {
                "roadmap_id": roadmap_id,
                "concept_id": concept_id,
                "ltm_count": ltm_count,
                "context_loaded": bool(context.get("roadmap_context")),
            }
        except Exception as exc:
            logger.warning(
                "mentor_warmup_partial_failed",
                user_id=user_id,
                roadmap_id=roadmap_id,
                error=str(exc),
            )
            return {"roadmap_id": roadmap_id, "concept_id": concept_id, "ltm_count": 0, "context_loaded": False}

    async def list_sessions(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        roadmap_id: str | None = None,
        scope: Literal["roadmap", "concept"] = "roadmap",
        concept_id: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ChatSession], int]:
        """
        获取会话列表
        """
        if scope == "concept" and not concept_id:
            raise errors.RequestError(msg="concept scope requires concept_id")

        sessions = await chat_session_crud.get_user_sessions(
            db,
            user_id=user_id,
            roadmap_id=roadmap_id,
            scope=scope,
            concept_id=concept_id,
            limit=limit,
            offset=offset,
        )
        total = await chat_session_crud.count_user_sessions(
            db,
            user_id=user_id,
            roadmap_id=roadmap_id,
            scope=scope,
            concept_id=concept_id,
        )
        return sessions, total

    async def get_session(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        session_id: str,
    ) -> ChatSession:
        """
        获取指定会话详情
        """
        chat_session = await chat_session_crud.get_by_id(db, session_id)
        if chat_session is None or chat_session.user_id != user_id:
            raise errors.NotFoundError(msg="会话不存在")
        return chat_session

    async def create_session(
        self,
        *,
        db: AsyncSession,
        user_id: str,
        roadmap_id: str,
        concept_id: str | None = None,
        title: str | None = None,
        agent_type: str = "tutoring",
        model_id: str | None = None,
    ) -> ChatSession:
        """
        创建会话
        """
        await self._ensure_roadmap_access(
            db,
            user_id=user_id,
            roadmap_id=roadmap_id,
        )
        async with async_session_maker.begin() as session:
            return await chat_session_crud.create_session(
                session,
                user_id=user_id,
                roadmap_id=roadmap_id,
                concept_id=concept_id,
                title=title,
                agent_type=agent_type,
                model_id=model_id,
            )

    async def get_session_messages(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[ChatSession, list[ChatMessage], int]:
        """
        获取指定会话消息
        """
        chat_session = await chat_session_crud.get_by_id(db, session_id)
        if chat_session is None or chat_session.user_id != user_id:
            raise errors.NotFoundError(msg="会话不存在")

        messages = await chat_message_crud.get_by_session(
            db,
            session_id=session_id,
            limit=limit,
            offset=offset,
        )
        total = await chat_message_crud.count_by_session(db, session_id)
        return chat_session, messages, total

    async def delete_session(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        session_id: str,
    ) -> ChatSession:
        """
        删除指定会话及其关联数据
        """
        chat_session = await chat_session_crud.get_by_id(db, session_id)
        if chat_session is None or chat_session.user_id != user_id:
            raise errors.NotFoundError(msg="会话不存在")

        deleted_session = await chat_session_crud.delete_session_tree(
            db,
            session_id=session_id,
        )
        if deleted_session is None:
            raise errors.NotFoundError(msg="会话不存在")

        return deleted_session

    async def rebuild_short_term_memory(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        session_id: str,
    ) -> int:
        """
        重建短期记忆窗口
        """
        chat_session = await chat_session_crud.get_by_id(db, session_id)
        if chat_session is None or chat_session.user_id != user_id:
            raise errors.NotFoundError(msg="会话不存在")

        messages = await self.context_service.rebuild_short_term_messages(
            db,
            session_id=session_id,
        )
        return len(messages)

    async def get_memory_job(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        job_id: str,
    ) -> MentorMemoryJob:
        """
        获取记忆任务
        """
        job = await mentor_memory_job_crud.get_by_job_id(db, job_id)
        if job is None or job.user_id != user_id:
            raise errors.NotFoundError(msg="记忆任务不存在")
        return job

    async def replay_memory_job(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        message_id: str,
    ) -> MentorMemoryJob:
        """
        重放记忆任务
        """
        job = await mentor_memory_job_crud.get_by_message_id(db, message_id)
        if job is None or job.user_id != user_id:
            raise errors.NotFoundError(msg="记忆任务不存在")

        payload = dict(job.payload or {})
        payload["job_id"] = job.job_id
        payload["message_id"] = job.message_id
        celery_result = celery_app.send_task(
            "mentor.persist_and_extract_memory",
            kwargs=payload,
        )

        async with async_session_maker.begin() as session:
            replay_job = await mentor_memory_job_crud.reset_for_replay(
                session,
                celery_task_id=celery_result.id,
                job_id=job.job_id,
            )
        return replay_job or job

    async def _prepare_context_with_access(
        self,
        db: AsyncSession,
        *,
        current_user: User,
        request: MentorChatRequest,
    ) -> dict:
        """
        合并路线图权限校验与学习上下文构建

        相较于原来分开调用 _ensure_roadmap_access + get_learning_context，
        此方法只执行一次 roadmap 数据库查询，并将结果同时用于权限校验和上下文提取。
        """
        roadmap_id = request.context.roadmap_id
        roadmap = await self.roadmap_crud.get_by_roadmap_id(db, roadmap_id)

        if roadmap is None:
            raise errors.NotFoundError(msg="路线图不存在")
        if roadmap.user_id != current_user.id and roadmap.user_id != settings.FEATURED_USER_ID:
            raise errors.ForbiddenError(msg="无权访问该路线图")

        # 优先读取预热缓存，缓存未命中时利用已查到的 roadmap 构建（避免二次 roadmap 查询）
        learning_context = await self.context_service.get_learning_context_from_roadmap_cached(
            db,
            roadmap=roadmap,
            roadmap_id=roadmap_id,
            concept_id=request.context.concept_id,
        )

        # 前端传入的上下文覆盖数据库值（前端感知更实时）
        if request.context.concept_title:
            learning_context["concept_title"] = request.context.concept_title
        if request.context.tutorial_excerpt:
            learning_context["tutorial_excerpt"] = request.context.tutorial_excerpt[
                : settings.MENTOR_CONTEXT_EXCERPT_MAX_LENGTH
            ]
        if request.context.roadmap_context:
            learning_context["roadmap_context"] = request.context.roadmap_context

        return learning_context

    async def _ensure_roadmap_access(
        self,
        db: AsyncSession,
        *,
        user_id: str,
        roadmap_id: str,
    ) -> None:
        """
        校验路线图访问权限（供其他非聊天场景调用）
        """
        roadmap = await self.roadmap_crud.get_by_roadmap_id(db, roadmap_id)
        if roadmap is None:
            raise errors.NotFoundError(msg="路线图不存在")

        if roadmap.user_id != user_id and roadmap.user_id != settings.FEATURED_USER_ID:
            raise errors.ForbiddenError(msg="无权访问该路线图")

    async def _ensure_session_exists(
        self,
        *,
        user_id: str,
        session_id: str,
        request: MentorChatRequest,
    ) -> None:
        """
        确保会话存在
        """
        async with async_session_maker.begin() as session:
            existing = await chat_session_crud.get_by_id(session, session_id)
            if existing is not None:
                return

            title = request.context.concept_title or request.message[:20]
            await chat_session_crud.create(
                session,
                obj_in={
                    "session_id": session_id,
                    "user_id": user_id,
                    "roadmap_id": request.context.roadmap_id,
                    "concept_id": request.context.concept_id,
                    "title": title,
                    "agent_type": request.agent_type,
                    "model_id": request.model_id or settings.MENTOR_AGENT_MODEL,
                },
            )

    async def _persist_chat_round(
        self,
        *,
        current_user: User,
        request: MentorChatRequest,
        session_id: str,
        trace_id: str,
        user_message_id: str,
        assistant_message_id: str,
        assistant_message: str,
    ) -> None:
        """
        同步持久化本轮聊天消息与会话元数据

        设计说明：
        - 前端在收到 SSE meta 后会立刻将本地线程绑定到远端 session
        - 若消息仅依赖异步 Celery Worker 落库，前端随后的 hydrate 会拿到 0 条消息并覆盖掉刚显示的内容
        - 因此这里先同步落库，确保首轮流式回答结束后即可被历史接口读取
        """
        assistant_message = self._sanitize_assistant_message(assistant_message)
        model_id = request.model_id or settings.MENTOR_AGENT_MODEL

        async with async_session_maker.begin() as session:
            persisted_user_message = await chat_message_crud.get(session, user_message_id)
            if persisted_user_message is None:
                await chat_message_crud.create_message(
                    session,
                    message_id=user_message_id,
                    session_id=session_id,
                    role="user",
                    content=request.message,
                    agent_type=request.agent_type,
                    model_id=model_id,
                    trace_id=trace_id,
                    message_metadata={
                        "roadmap_id": request.context.roadmap_id,
                        "concept_id": request.context.concept_id,
                    },
                )

            persisted_assistant_message = await chat_message_crud.get(session, assistant_message_id)
            if persisted_assistant_message is None:
                await chat_message_crud.create_message(
                    session,
                    message_id=assistant_message_id,
                    session_id=session_id,
                    role="assistant",
                    content=assistant_message,
                    agent_type=request.agent_type,
                    model_id=model_id,
                    trace_id=trace_id,
                    message_metadata={
                        "roadmap_id": request.context.roadmap_id,
                        "concept_id": request.context.concept_id,
                    },
                )

            message_count = await chat_message_crud.count_by_session(session, session_id)
            await chat_session_crud.update_metadata(
                session,
                session_id,
                message_count=message_count,
                last_message_preview=assistant_message[:120],
                title=request.context.concept_title or request.message[:20],
                model_id=model_id,
                agent_type=request.agent_type,
            )

    async def _dispatch_memory_job(
        self,
        *,
        current_user: User,
        request: MentorChatRequest,
        session_id: str,
        trace_id: str,
        user_message_id: str,
        assistant_message_id: str,
        assistant_message: str,
    ) -> None:
        """
        投递异步记忆任务并写入任务审计记录
        """
        assistant_message = self._sanitize_assistant_message(assistant_message)
        payload = {
            "job_id": str(uuid.uuid4()),
            "message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "user_id": current_user.id,
            "session_id": session_id,
            "roadmap_id": request.context.roadmap_id,
            "concept_id": request.context.concept_id,
            "agent_type": request.agent_type,
            "model_id": request.model_id or settings.MENTOR_AGENT_MODEL,
            "trace_id": trace_id,
            "user_message": request.message,
            "assistant_message": assistant_message,
            "context": request.context.model_dump(),
        }

        try:
            celery_result = celery_app.send_task(
                "mentor.persist_and_extract_memory",
                kwargs=payload,
            )
        except Exception as exc:
            logger.exception("mentor_memory_job_dispatch_failed", error=str(exc), session_id=session_id)
            async with async_session_maker.begin() as session:
                created_job = await mentor_memory_job_crud.create_job(
                    session,
                    job_id=payload["job_id"],
                    message_id=payload["message_id"],
                    user_id=current_user.id,
                    session_id=session_id,
                    payload=payload,
                    celery_task_id=None,
                )
                await mentor_memory_job_crud.mark_failed(
                    session,
                    job_id=created_job.job_id,
                    last_error=str(exc),
                    retry_count=0,
                    dead_letter=False,
                )
            return

        async with async_session_maker.begin() as session:
            await mentor_memory_job_crud.create_job(
                session,
                job_id=payload["job_id"],
                message_id=payload["message_id"],
                user_id=current_user.id,
                session_id=session_id,
                payload=payload,
                celery_task_id=celery_result.id,
            )

    @staticmethod
    def _build_learning_profile(current_user: User) -> str | None:
        """
        构建轻量级学习画像
        """
        if current_user.username:
            return f"当前用户昵称：{current_user.username}"
        if current_user.email:
            return f"当前用户邮箱：{current_user.email}"
        return None

    @classmethod
    def _sanitize_assistant_message(cls, content: str) -> str:
        """
        清洗导师回复中的不稳定 Markdown，保证前端渲染一致

        Args:
            content: 模型原始输出文本

        Returns:
            适合前端 Markdown 渲染的清洗后文本

        Raises:
            无
        """
        normalized_content = content.replace("\r\n", "\n").strip()
        if not normalized_content:
            return ""

        normalized_content = cls.MARKDOWN_HORIZONTAL_RULE_PATTERN.sub("", normalized_content)
        normalized_content = cls._normalize_inline_markdown_spacing(
            normalized_content,
            pattern=cls.INLINE_BOLD_PATTERN,
        )
        normalized_content = cls._normalize_inline_markdown_spacing(
            normalized_content,
            pattern=cls.INLINE_CODE_PATTERN,
        )
        normalized_content = re.sub(r"\n{3,}", "\n\n", normalized_content)
        return normalized_content.strip()

    @classmethod
    def _normalize_inline_markdown_spacing(cls, content: str, *, pattern: re.Pattern[str]) -> str:
        """
        为行内 Markdown 两侧补齐必要空格

        Args:
            content: 待处理文本
            pattern: 行内 Markdown 正则

        Returns:
            修正空格后的文本

        Raises:
            无
        """
        cursor = 0
        output_parts: list[str] = []

        # 这里按 match 逐段重建字符串，避免多次正则替换互相影响位置。
        for match in pattern.finditer(content):
            start, end = match.span()
            inline_token = match.group(0)

            if start > 0 and cls._needs_spacing(content[start - 1]):
                inline_token = f" {inline_token}"
            if end < len(content) and cls._needs_spacing(content[end]):
                inline_token = f"{inline_token} "

            output_parts.append(content[cursor:start])
            output_parts.append(inline_token)
            cursor = end

        if not output_parts:
            return content

        output_parts.append(content[cursor:])
        return "".join(output_parts)

    @classmethod
    def _needs_spacing(cls, char: str) -> bool:
        """
        判断某个相邻字符是否需要与行内 Markdown 之间补空格

        Args:
            char: 待判断字符

        Returns:
            是否需要补空格

        Raises:
            无
        """
        return bool(cls.INLINE_MARKDOWN_ADJACENT_PATTERN.match(char))

    @classmethod
    def _build_incremental_sanitized_delta(
        cls,
        *,
        raw_text: str,
        emitted_length: int,
        is_final: bool = False,
    ) -> tuple[str, int]:
        """
        从原始流式文本中提取可安全发送给前端的增量片段

        Args:
            raw_text: 当前累计的原始文本
            emitted_length: 已发送给前端的清洗后文本长度
            is_final: 是否为最终收尾阶段

        Returns:
            新增可发送片段与更新后的已发送长度

        Raises:
            无
        """
        sanitized_text = cls._sanitize_assistant_message(raw_text)
        if not is_final:
            if len(sanitized_text) <= cls.STREAM_SANITIZE_HOLDBACK_CHARS:
                return "", emitted_length
            stable_text = sanitized_text[:-cls.STREAM_SANITIZE_HOLDBACK_CHARS]
        else:
            stable_text = sanitized_text

        if emitted_length > len(stable_text):
            emitted_length = len(stable_text)

        return stable_text[emitted_length:], len(stable_text)

    @staticmethod
    def _build_stream_error_message(exc: Exception) -> str:
        """
        将模型调用异常转换为可直接返回给前端的提示文案
        """
        if isinstance(exc, AuthenticationError):
            return "当前模型服务鉴权失败，请联系管理员检查 provider、base_url 或 API Key 配置。"

        if isinstance(exc, BadRequestError):
            return "当前模型名称不可用或请求格式不被支持，请切换其他模型名称后重试。"

        return "AI 伴学助手暂时不可用，请稍后再试。"

    @staticmethod
    def _build_sse_payload(payload: dict) -> str:
        """
        构建 SSE 数据帧
        """
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


mentor_service = MentorService()


def get_mentor_service() -> MentorService:
    """
    获取 AI 伴学助手服务单例
    """
    return mentor_service
