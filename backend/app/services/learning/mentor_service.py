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
from app.config.settings import settings
from app.core.observability import (
    build_mentor_trace_metadata,
    create_langfuse_trace_id,
    flush_langfuse,
    propagate_mentor_attributes,
    start_langfuse_observation,
    update_current_span_safely,
)
from app.core.celery_app import celery_app
from app.core.custom_exceptions import errors
from app.crud.crud_chat import chat_message_crud, chat_session_crud
from app.crud.crud_mentor_memory_job import mentor_memory_job_crud
from app.crud.crud_roadmap import get_roadmap_crud
from app.db.session import async_session_maker
from app.models.database import ChatMessage, ChatSession, MentorMemoryJob, User
from app.schemas.mentor import MentorChatRequest
from app.services.learning.mentor import (
    MentorEmotionAnalysis,
    MentorPlaceholderAgentInput,
    MentorQaAgentInput,
    MentorTextDeltaEvent,
    MentorThinkingDeltaEvent,
    MentorToolResultEvent,
    MentorToolStartEvent,
)
from app.services.learning.mentor.agent_registry import MentorAgentRegistry
from app.services.learning.mentor_context_service import (
    MentorContextService,
    get_mentor_context_service,
)
from app.services.learning.mentor_rate_limit_service import (
    MentorRateLimitService,
    get_mentor_rate_limit_service,
)
from app.services.shared.mentor_model_registry_service import (
    MentorModelRegistryService,
    get_mentor_model_registry_service,
)

logger = structlog.get_logger()


@dataclass(slots=True)
class MentorChatStreamContext:
    """
    AI 伴学助手流式上下文
    """

    session_id: str
    trace_id: str
    langfuse_trace_id: str
    user_message_id: str
    assistant_message_id: str
    stream: AsyncGenerator[str, None]


@dataclass(slots=True)
class MentorChatAgentContext:
    """
    当前聊天轮次的 Agent 上下文
    """

    agent_kind: str
    qa_style: str | None
    emotion: MentorEmotionAnalysis


class MentorService:
    """
    AI 伴学助手服务
    """

    STREAM_SANITIZE_HOLDBACK_CHARS = 8
    MARKDOWN_HORIZONTAL_RULE_PATTERN = re.compile(r"(?m)^[ \t]{0,3}(?:---|\*\*\*|___)[ \t]*$")
    DOUBLE_BACKTICK_INLINE_CODE_PATTERN = re.compile(r"(?<!`)``([^`\n]+?)``(?!`)")
    DOUBLE_BACKTICK_WRAPPED_INLINE_CODE_PATTERN = re.compile(
        r"(?<!`)``\s*`([^`\n]+)`\s*``(?!`)"
    )
    INLINE_BOLD_PATTERN = re.compile(r"\*\*[^*\n]+?\*\*")
    INLINE_CODE_PATTERN = re.compile(r"(?<!`)`[^`\n]+`(?!`)")
    INLINE_MARKDOWN_ADJACENT_PATTERN = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]")
    EMOJI_PATTERN = re.compile(
        "["
        "\U0001F300-\U0001FAD6"
        "\U0001FAE0-\U0001FAFF"
        "\U00002700-\U000027BF"
        "\u2600-\u26FF"
        "\uFE0F"
        "]+",
        flags=re.UNICODE,
    )

    def __init__(
        self,
        *,
        agent_factory: AgentFactory | None = None,
        context_service: MentorContextService | None = None,
        rate_limit_service: MentorRateLimitService | None = None,
        model_registry_service: MentorModelRegistryService | None = None,
    ) -> None:
        self.agent_factory = agent_factory or get_agent_factory()
        self.context_service = context_service or get_mentor_context_service()
        self.rate_limit_service = rate_limit_service or get_mentor_rate_limit_service()
        self.model_registry_service = model_registry_service or get_mentor_model_registry_service()
        self.roadmap_crud = get_roadmap_crud()
        self.roadmap_crud = get_roadmap_crud()

    @staticmethod
    def _analyze_user_emotion(message: str) -> MentorEmotionAnalysis:
        """
        基于轻量规则判断用户当前情绪
        """

        normalized_message = message.strip().lower()
        if not normalized_message:
            return MentorEmotionAnalysis(label="neutral", summary="用户语气平稳，未显著暴露情绪。")

        anxious_keywords = ("不会", "看不懂", "好难", "卡住", "崩溃", "焦虑", "迷茫", "不会做")
        frustrated_keywords = ("报错", "错误", "怎么不行", "为什么不", "没反应", "有问题", "bug")
        curious_keywords = ("为什么", "原理", "区别", "举例", "怎么理解", "是什么")

        if any(keyword in normalized_message for keyword in anxious_keywords):
            return MentorEmotionAnalysis(label="anxious", summary="用户当前有明显卡住或焦虑倾向，需要先降低理解门槛。")

        if any(keyword in normalized_message for keyword in frustrated_keywords):
            return MentorEmotionAnalysis(label="frustrated", summary="用户当前带有排错或受阻情绪，需要先快速定位问题。")

        if any(keyword in normalized_message for keyword in curious_keywords):
            return MentorEmotionAnalysis(label="curious", summary="用户当前偏探索和求知，适合给出清晰解释与例子。")

        return MentorEmotionAnalysis(label="neutral", summary="用户语气平稳，适合直接进入问题解答。")

    def _create_chat_agent(
        self,
        *,
        agent_kind: str,
        runtime_model_config,
    ):
        """
        按静态 Agent 类型创建聊天运行时
        """

        if agent_kind == "qa":
            return self.agent_factory.create_qa_agent(runtime_config=runtime_model_config)
        if agent_kind == "guide":
            return self.agent_factory.create_guide_agent(runtime_config=runtime_model_config)
        if agent_kind == "quiz":
            return self.agent_factory.create_quiz_agent(runtime_config=runtime_model_config)
        raise errors.BadRequestError(msg=f"不支持的聊天 Agent 类型：{agent_kind}")

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
        langfuse_trace_id = create_langfuse_trace_id(trace_id)
        user_message_id = str(uuid.uuid4())
        assistant_message_id = str(uuid.uuid4())
        agent_kind = request.agent_kind
        if not MentorAgentRegistry.is_supported(agent_kind):
            raise errors.BadRequestError(msg=f"不支持的聊天 Agent 类型：{agent_kind}")
        runtime_model_config = await self.model_registry_service.get_runtime_config(
            db,
            model_id=request.model_id,
            user_id=current_user.id,
        )
        request_model_id = request.model_id or runtime_model_config.model_id

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
                resolved_agent_type=agent_kind,
                model_id=request_model_id,
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
        agent_context = MentorChatAgentContext(
            agent_kind=agent_kind,
            qa_style=request.qa_style if agent_kind == "qa" else None,
            emotion=self._analyze_user_emotion(request.message),
        )
        logger.info(
            "mentor_chat_agent_resolved",
            user_id=current_user.id,
            session_id=session_id,
            trace_id=trace_id,
            agent_kind=agent_context.agent_kind,
            qa_style=agent_context.qa_style,
            emotion_label=agent_context.emotion.label,
        )

        learning_profile = self._build_learning_profile(current_user)
        agent = self._create_chat_agent(
            agent_kind=agent_context.agent_kind,
            runtime_model_config=runtime_model_config,
        )
        if agent_context.agent_kind == "qa":
            agent_input = MentorQaAgentInput(
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
                qa_style=agent_context.qa_style or "casual",
                emotion=agent_context.emotion,
                trace_id=trace_id,
                langfuse_trace_id=langfuse_trace_id,
            )
        else:
            agent_input = MentorPlaceholderAgentInput(
                user_message=request.message,
                concept_title=learning_context.get("concept_title"),
                agent_kind=agent_context.agent_kind,
            )

        async def event_stream() -> AsyncGenerator[str, None]:
            """
            SSE 事件流
            """
            raw_assistant_text = ""
            emitted_length = 0
            persisted_content_parts: list[dict] = []
            request_metadata = build_mentor_trace_metadata(
                external_trace_id=trace_id,
                user_id=current_user.id,
                session_id=session_id,
                roadmap_id=request.context.roadmap_id,
                concept_id=request.context.concept_id,
                agent_id=agent.agent_id,
                agent_type=agent_context.agent_kind,
                model=runtime_model_config.model_name,
                provider=runtime_model_config.provider,
                assist_mode="answer",
                resolved_assist_mode="answer",
                prompt_template=getattr(agent, "get_template_name", lambda: None)(),
                extra_metadata={
                    "emotion_label": agent_context.emotion.label,
                    "emotion_summary": agent_context.emotion.summary,
                    "history_message_count": len(history_messages),
                    "ltm_fact_count": len(ltm_facts),
                    "model_id": request_model_id,
                    "resolved_model_name": runtime_model_config.model_name,
                    "langfuse_trace_id": langfuse_trace_id,
                    "qa_style": agent_context.qa_style,
                },
            )
            request_input = {
                "message_length": len(request.message),
                "roadmap_id": request.context.roadmap_id,
                "concept_id": request.context.concept_id,
                "model_id": request_model_id,
                "resolved_model_name": runtime_model_config.model_name,
                "agent_kind": agent_context.agent_kind,
                "qa_style": agent_context.qa_style,
                "emotion_label": agent_context.emotion.label,
            }

            try:
                with propagate_mentor_attributes(
                    user_id=current_user.id,
                    session_id=session_id,
                    trace_name="mentor.chat.stream",
                    metadata={
                        "external_trace_id": trace_id,
                        "langfuse_trace_id": langfuse_trace_id,
                        "roadmap_id": request.context.roadmap_id,
                        "concept_id": request.context.concept_id,
                        "agent_type": agent_context.agent_kind,
                    },
                    tags=["mentor", agent_context.agent_kind],
                ):
                    with start_langfuse_observation(
                        name="mentor.chat.stream",
                        as_type="span",
                        trace_id=langfuse_trace_id,
                        input=request_input,
                        metadata=request_metadata,
                    ):
                        yield self._build_sse_payload(
                            {
                                "type": "meta",
                                "session_id": session_id,
                                "trace_id": trace_id,
                                "langfuse_trace_id": langfuse_trace_id,
                                "user_message_id": user_message_id,
                                "assistant_message_id": assistant_message_id,
                                "agent_kind": agent_context.agent_kind,
                                "qa_style": agent_context.qa_style,
                                "emotion_label": agent_context.emotion.label,
                                "emotion_summary": agent_context.emotion.summary,
                            }
                        )

                        persist_succeeded = False
                        memory_job_enqueued = False

                        try:
                            async for event in agent.stream_chat(agent_input):
                                if isinstance(event, MentorThinkingDeltaEvent):
                                    self._append_thinking_content_part(
                                        persisted_content_parts,
                                        event.delta,
                                    )
                                    yield self._build_sse_payload(
                                        {
                                            "type": "thinking",
                                            "delta": event.delta,
                                        }
                                    )
                                    continue

                                if isinstance(event, MentorTextDeltaEvent):
                                    raw_assistant_text += event.delta
                                    sanitized_delta, emitted_length = self._build_incremental_sanitized_delta(
                                        raw_text=raw_assistant_text,
                                        emitted_length=emitted_length,
                                    )
                                    if sanitized_delta:
                                        self._append_text_content_part(
                                            persisted_content_parts,
                                            sanitized_delta,
                                        )
                                        yield self._build_sse_payload(
                                            {"type": "delta", "delta": sanitized_delta}
                                        )
                                    continue

                                if isinstance(event, MentorToolStartEvent):
                                    self._upsert_tool_content_part(
                                        persisted_content_parts,
                                        tool_call_id=event.tool_call_id,
                                        tool_name=event.tool_name,
                                        arguments=event.arguments,
                                        state="running",
                                    )
                                    yield self._build_sse_payload(
                                        {
                                            "type": "tool_start",
                                            "tool_call_id": event.tool_call_id,
                                            "tool_name": event.tool_name,
                                            "arguments": event.arguments,
                                        }
                                    )
                                    continue

                                if isinstance(event, MentorToolResultEvent):
                                    self._upsert_tool_content_part(
                                        persisted_content_parts,
                                        tool_call_id=event.tool_call_id,
                                        tool_name=event.tool_name,
                                        arguments=event.arguments,
                                        state="completed",
                                        result=event.result,
                                        is_error=event.is_error,
                                    )
                                    yield self._build_sse_payload(
                                        {
                                            "type": "tool_result",
                                            "tool_call_id": event.tool_call_id,
                                            "tool_name": event.tool_name,
                                            "arguments": event.arguments,
                                            "result": event.result,
                                            "is_error": event.is_error,
                                        }
                                    )
                        except Exception as exc:
                            logger.exception(
                                "mentor_chat_stream_failed",
                                user_id=current_user.id,
                                session_id=session_id,
                                error=str(exc),
                            )
                            update_current_span_safely(
                                output={
                                    "status": "stream_failed",
                                    "assistant_message_length": len(raw_assistant_text),
                                },
                                metadata={"error_type": type(exc).__name__},
                                level="ERROR",
                                status_message=str(exc),
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
                            if not persisted_content_parts:
                                self._append_text_content_part(
                                    persisted_content_parts,
                                    assistant_message,
                                )
                        final_delta = assistant_message[emitted_length:]
                        if final_delta:
                            self._append_text_content_part(persisted_content_parts, final_delta)
                            yield self._build_sse_payload({"type": "delta", "delta": final_delta})

                        try:
                            await self._persist_chat_round(
                                current_user=current_user,
                                request=request,
                                model_id=request_model_id,
                                session_id=session_id,
                                trace_id=trace_id,
                                user_message_id=user_message_id,
                                assistant_message_id=assistant_message_id,
                                assistant_message=assistant_message,
                                assistant_content_parts=persisted_content_parts,
                                agent_context=agent_context,
                            )
                            persist_succeeded = True
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
                                model_id=request_model_id,
                                resolved_model_name=runtime_model_config.model_name,
                                provider=runtime_model_config.provider,
                                session_id=session_id,
                                trace_id=trace_id,
                                langfuse_trace_id=langfuse_trace_id,
                                user_message_id=user_message_id,
                                assistant_message_id=assistant_message_id,
                                assistant_message=assistant_message,
                                agent_context=agent_context,
                            )
                            memory_job_enqueued = True
                        except Exception as exc:
                            logger.exception(
                                "mentor_memory_job_dispatch_failed",
                                user_id=current_user.id,
                                session_id=session_id,
                                trace_id=trace_id,
                                error=str(exc),
                            )

                        update_current_span_safely(
                            output={
                                "status": "completed",
                                "assistant_message_length": len(assistant_message),
                                "persist_succeeded": persist_succeeded,
                                "memory_job_enqueued": memory_job_enqueued,
                            }
                        )
                        flush_langfuse()
                        yield "data: [DONE]\n\n"
            finally:
                flush_langfuse()

        return MentorChatStreamContext(
            session_id=session_id,
            trace_id=trace_id,
            langfuse_trace_id=langfuse_trace_id,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
            stream=event_stream(),
        )

    async def list_available_models(
        self,
        db: AsyncSession,
        *,
        user_id: str,
    ) -> tuple[list, str | None]:
        """
        获取 Mentor 前端可用模型列表
        """
        return await self.model_registry_service.list_available_models(
            db,
            user_id=user_id,
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
        resolved_agent_type: str,
        model_id: str,
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
                    "agent_type": resolved_agent_type,
                    "model_id": model_id,
                },
            )

    async def _persist_chat_round(
        self,
        *,
        current_user: User,
        request: MentorChatRequest,
        model_id: str,
        session_id: str,
        trace_id: str,
        user_message_id: str,
        assistant_message_id: str,
        assistant_message: str,
        assistant_content_parts: list[dict] | None,
        agent_context: MentorChatAgentContext,
    ) -> None:
        """
        同步持久化本轮聊天消息与会话元数据

        设计说明：
        - 前端在收到 SSE meta 后会立刻将本地线程绑定到远端 session
        - 若消息仅依赖异步 Celery Worker 落库，前端随后的 hydrate 会拿到 0 条消息并覆盖掉刚显示的内容
        - 因此这里先同步落库，确保首轮流式回答结束后即可被历史接口读取
        """
        assistant_message = self._sanitize_assistant_message(assistant_message)
        user_message_metadata = self._build_message_metadata(
            request=request,
            agent_context=agent_context,
        )
        assistant_message_metadata = self._build_message_metadata(
            request=request,
            agent_context=agent_context,
            content_parts=assistant_content_parts,
        )

        async with async_session_maker.begin() as session:
            persisted_user_message = await chat_message_crud.get(session, user_message_id)
            if persisted_user_message is None:
                await chat_message_crud.create_message(
                    session,
                    message_id=user_message_id,
                    session_id=session_id,
                    role="user",
                    content=request.message,
                    agent_type=agent_context.agent_kind,
                    model_id=model_id,
                    trace_id=trace_id,
                    message_metadata=user_message_metadata,
                    intent_type=agent_context.agent_kind,
                )

            persisted_assistant_message = await chat_message_crud.get(session, assistant_message_id)
            if persisted_assistant_message is None:
                await chat_message_crud.create_message(
                    session,
                    message_id=assistant_message_id,
                    session_id=session_id,
                    role="assistant",
                    content=assistant_message,
                    agent_type=agent_context.agent_kind,
                    model_id=model_id,
                    trace_id=trace_id,
                    message_metadata=assistant_message_metadata,
                    intent_type=agent_context.agent_kind,
                )

            message_count = await chat_message_crud.count_by_session(session, session_id)
            await chat_session_crud.update_metadata(
                session,
                session_id,
                message_count=message_count,
                last_message_preview=assistant_message[:120],
                title=request.context.concept_title or request.message[:20],
                model_id=model_id,
                agent_type=agent_context.agent_kind,
            )

    async def _dispatch_memory_job(
        self,
        *,
        current_user: User,
        request: MentorChatRequest,
        model_id: str,
        resolved_model_name: str,
        provider: str,
        session_id: str,
        trace_id: str,
        langfuse_trace_id: str,
        user_message_id: str,
        assistant_message_id: str,
        assistant_message: str,
        agent_context: MentorChatAgentContext,
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
            "agent_type": agent_context.agent_kind,
            "agent_kind": agent_context.agent_kind,
            "qa_style": agent_context.qa_style,
            "emotion_label": agent_context.emotion.label,
            "emotion_summary": agent_context.emotion.summary,
            "intent_type": agent_context.agent_kind,
            "model_id": model_id,
            "trace_id": trace_id,
            "langfuse_trace_id": langfuse_trace_id,
            "user_message": request.message,
            "assistant_message": assistant_message,
            "context": request.context.model_dump(),
        }

        dispatch_metadata = build_mentor_trace_metadata(
            external_trace_id=trace_id,
            user_id=current_user.id,
            session_id=session_id,
            roadmap_id=request.context.roadmap_id,
            concept_id=request.context.concept_id,
            agent_type=agent_context.agent_kind,
            model=resolved_model_name,
            provider=provider,
            queue_name="mentor_persist",
            job_id=payload["job_id"],
            extra_metadata={
                "intent_type": agent_context.agent_kind,
                "qa_style": agent_context.qa_style,
                "emotion_label": agent_context.emotion.label,
            },
        )
        dispatch_input = {
            "job_id": payload["job_id"],
            "session_id": session_id,
            "message_id": user_message_id,
            "assistant_message_id": assistant_message_id,
            "queue_name": "mentor_persist",
        }

        with start_langfuse_observation(
            name="mentor.memory_job.dispatch",
            as_type="span",
            input=dispatch_input,
            metadata=dispatch_metadata,
        ):
            try:
                celery_result = celery_app.send_task(
                    "mentor.persist_and_extract_memory",
                    kwargs=payload,
                )
            except Exception as exc:
                logger.exception("mentor_memory_job_dispatch_failed", error=str(exc), session_id=session_id)
                update_current_span_safely(
                    output={"status": "dispatch_failed"},
                    metadata={"error_type": type(exc).__name__},
                    level="ERROR",
                    status_message=str(exc),
                )
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

            update_current_span_safely(
                output={
                    "status": "queued",
                    "celery_task_id": celery_result.id,
                }
            )

    @staticmethod
    def _append_text_content_part(content_parts: list[dict], text: str) -> None:
        """
        追加文本内容片段，并自动合并相邻文本块
        """
        if not text:
            return

        if content_parts and content_parts[-1].get("type") == "text":
            content_parts[-1]["text"] = f"{content_parts[-1].get('text', '')}{text}"
            return

        content_parts.append(
            {
                "type": "text",
                "text": text,
            }
        )

    @staticmethod
    def _append_thinking_content_part(content_parts: list[dict], text: str) -> None:
        """
        追加思考内容片段，并自动合并相邻思考块
        """
        if not text:
            return

        if content_parts and content_parts[-1].get("type") == "thinking":
            content_parts[-1]["text"] = f"{content_parts[-1].get('text', '')}{text}"
            return

        content_parts.append(
            {
                "type": "thinking",
                "text": text,
            }
        )

    @staticmethod
    def _upsert_tool_content_part(
        content_parts: list[dict],
        *,
        tool_call_id: str,
        tool_name: str,
        arguments: dict,
        state: str,
        result: str | None = None,
        is_error: bool = False,
    ) -> None:
        """
        更新或创建工具内容片段，确保历史回放顺序与实时流一致
        """
        for part in content_parts:
            if part.get("type") == "tool-call" and part.get("toolCallId") == tool_call_id:
                part["toolName"] = tool_name
                part["arguments"] = arguments
                part["state"] = state
                if result is not None:
                    part["result"] = result
                part["isError"] = is_error
                return

        content_parts.append(
            {
                "type": "tool-call",
                "toolCallId": tool_call_id,
                "toolName": tool_name,
                "arguments": arguments,
                "state": state,
                "result": result,
                "isError": is_error,
            }
        )

    @staticmethod
    def _build_message_metadata(
        *,
        request: MentorChatRequest,
        agent_context: MentorChatAgentContext,
        content_parts: list[dict] | None = None,
    ) -> dict:
        """
        构建消息元数据，供前端 hydration 与埋点使用
        """
        metadata = {
            "roadmapId": request.context.roadmap_id,
            "conceptId": request.context.concept_id,
            "agentKind": agent_context.agent_kind,
            "agentType": agent_context.agent_kind,
            "qaStyle": agent_context.qa_style,
            "emotionLabel": agent_context.emotion.label,
            "emotionSummary": agent_context.emotion.summary,
            "intentType": agent_context.agent_kind,
        }
        if content_parts:
            metadata["contentParts"] = content_parts
        return metadata

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
        normalized_content = cls.EMOJI_PATTERN.sub("", normalized_content)
        normalized_content = cls.DOUBLE_BACKTICK_WRAPPED_INLINE_CODE_PATTERN.sub(
            r"`\1`",
            normalized_content,
        )
        normalized_content = cls.DOUBLE_BACKTICK_INLINE_CODE_PATTERN.sub(r"`\1`", normalized_content)
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
