"""
AI 伴学助手上下文编排服务
"""
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.crud.crud_chat import chat_message_crud
from app.crud.crud_roadmap import get_roadmap_crud
from app.crud.crud_tutorial import get_tutorial_crud
from app.db.redis_client import redis_client
from app.services.learning.memory_service import MemoryService, MentorMemoryFact, get_memory_service
from app.utils.serializers import fast_dumps, fast_loads

logger = structlog.get_logger()

# 表示"路线图级别"（未绑定 concept）的 scope 占位符
_ROADMAP_SCOPE = "__roadmap__"


class MentorContextService:
    """
    AI 伴学助手上下文编排服务
    """

    def __init__(self, memory_service: MemoryService | None = None) -> None:
        self.memory_service = memory_service or get_memory_service()
        self.roadmap_crud = get_roadmap_crud()
        self.tutorial_crud = get_tutorial_crud()

    @staticmethod
    def build_stm_key(session_id: str) -> str:
        """
        构建短期记忆 Redis Key
        """
        return f"mentor:stm:{session_id}"

    @staticmethod
    def build_ltm_cache_key(user_id: str, roadmap_id: str, concept_id: str | None) -> str:
        """
        构建长期记忆预热缓存 Redis Key

        格式：mentor:ltm_cache:{user_id}:{roadmap_id}:{concept_id or '__roadmap__'}
        """
        scope = concept_id or _ROADMAP_SCOPE
        return f"mentor:ltm_cache:{user_id}:{roadmap_id}:{scope}"

    @staticmethod
    def build_context_cache_key(roadmap_id: str, concept_id: str | None) -> str:
        """
        构建学习上下文预热缓存 Redis Key

        格式：mentor:context_cache:{roadmap_id}:{concept_id or '__roadmap__'}
        """
        scope = concept_id or _ROADMAP_SCOPE
        return f"mentor:context_cache:{roadmap_id}:{scope}"

    async def get_short_term_messages(
        self,
        db: AsyncSession,
        *,
        session_id: str,
    ) -> list[dict[str, Any]]:
        """
        读取短期记忆；缓存未命中时从数据库回补
        """
        await redis_client.connect()
        key = self.build_stm_key(session_id)
        raw_items = await redis_client._client.lrange(key, 0, settings.MENTOR_STM_WINDOW_SIZE - 1)
        if raw_items:
            cached_messages = [fast_loads(item) for item in raw_items]
            cached_messages.reverse()
            return cached_messages

        logger.info("mentor_stm_cache_miss", session_id=session_id)
        messages = await self.rebuild_short_term_messages(db, session_id=session_id)
        return messages

    async def rebuild_short_term_messages(
        self,
        db: AsyncSession,
        *,
        session_id: str,
    ) -> list[dict[str, Any]]:
        """
        从数据库重建短期记忆并回写 Redis
        """
        messages = await chat_message_crud.get_recent_messages(
            db,
            session_id=session_id,
            limit=settings.MENTOR_STM_WINDOW_SIZE,
        )
        payloads = [
            {
                "message_id": message.message_id,
                "role": message.role,
                "content": message.content,
                "created_at": message.created_at.isoformat() if message.created_at else None,
            }
            for message in messages
        ]

        await self.replace_short_term_messages(session_id=session_id, messages=payloads)
        return payloads

    async def append_short_term_messages(
        self,
        *,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> None:
        """
        追加短期记忆并维护滑动窗口
        """
        await redis_client.connect()
        key = self.build_stm_key(session_id)
        if not messages:
            return

        encoded_messages = [fast_dumps(message).decode("utf-8") for message in messages]
        pipe = redis_client._client.pipeline()
        pipe.lpush(key, *encoded_messages)
        pipe.ltrim(key, 0, settings.MENTOR_STM_WINDOW_SIZE - 1)
        pipe.expire(key, settings.MENTOR_STM_TTL_SECONDS)
        await pipe.execute()

    async def replace_short_term_messages(
        self,
        *,
        session_id: str,
        messages: list[dict[str, Any]],
    ) -> None:
        """
        重建整个短期记忆窗口
        """
        await redis_client.connect()
        key = self.build_stm_key(session_id)
        pipe = redis_client._client.pipeline()
        pipe.delete(key)
        if messages:
            encoded_messages = [fast_dumps(message).decode("utf-8") for message in messages]
            pipe.lpush(key, *encoded_messages)
            pipe.ltrim(key, 0, settings.MENTOR_STM_WINDOW_SIZE - 1)
            pipe.expire(key, settings.MENTOR_STM_TTL_SECONDS)
        await pipe.execute()

    async def get_long_term_memories(
        self,
        *,
        user_id: str,
        message: str,
    ) -> list[MentorMemoryFact]:
        """
        检索长期记忆（直接查询 Mem0，不经过缓存）
        """
        return await self.memory_service.search_memories(query=message, user_id=user_id)

    async def get_long_term_memories_cached(
        self,
        *,
        user_id: str,
        message: str,
        roadmap_id: str,
        concept_id: str | None,
    ) -> list[MentorMemoryFact]:
        """
        检索长期记忆（优先命中预热缓存，缓存未命中时回退到 Mem0 实时查询）

        缓存命中场景：用户进入路线图页面时已完成 warmup，消息发送时直接从 Redis 读取，
        避免每次发消息都触发 Mem0 向量搜索（通常 200-800ms）。
        """
        await redis_client.connect()
        cache_key = self.build_ltm_cache_key(user_id, roadmap_id, concept_id)

        try:
            raw = await redis_client._client.get(cache_key)
            if raw:
                cached_facts = fast_loads(raw)
                return [MentorMemoryFact(**item) for item in cached_facts]
        except Exception as exc:
            logger.warning("mentor_ltm_cache_read_failed", error=str(exc), cache_key=cache_key)

        # 缓存未命中：回退到 Mem0 实时查询
        logger.info("mentor_ltm_cache_miss", user_id=user_id, roadmap_id=roadmap_id, concept_id=concept_id)
        return await self.memory_service.search_memories(query=message, user_id=user_id)

    async def warmup_ltm_cache(
        self,
        *,
        user_id: str,
        roadmap_id: str,
        concept_id: str | None,
        warmup_query: str,
    ) -> int:
        """
        预热长期记忆缓存

        使用 concept_title 或 roadmap 名称作为预查询，将检索结果写入 Redis，
        供该 scope 下的后续对话直接读取，避免重复调用 Mem0 向量搜索。

        Returns:
            写入缓存的记忆条数
        """
        if not settings.MEM0_ENABLED:
            return 0

        facts = await self.memory_service.search_memories(query=warmup_query, user_id=user_id)
        cache_key = self.build_ltm_cache_key(user_id, roadmap_id, concept_id)
        payload = [fact.model_dump() for fact in facts]

        try:
            await redis_client.connect()
            await redis_client._client.setex(
                cache_key,
                settings.MENTOR_LTM_CACHE_TTL_SECONDS,
                fast_dumps(payload),
            )
        except Exception as exc:
            logger.warning("mentor_ltm_cache_write_failed", error=str(exc), cache_key=cache_key)

        return len(facts)

    async def invalidate_ltm_cache(
        self,
        *,
        user_id: str,
        roadmap_id: str,
        concept_id: str | None,
    ) -> None:
        """
        使长期记忆缓存失效

        在 Celery 记忆提炼任务完成后调用，确保下次对话读取到最新的记忆内容。
        """
        cache_key = self.build_ltm_cache_key(user_id, roadmap_id, concept_id)
        try:
            await redis_client.connect()
            await redis_client._client.delete(cache_key)
            logger.info("mentor_ltm_cache_invalidated", user_id=user_id, cache_key=cache_key)
        except Exception as exc:
            logger.warning("mentor_ltm_cache_invalidate_failed", error=str(exc), cache_key=cache_key)

    @staticmethod
    def build_long_term_memory_summary(facts: list[MentorMemoryFact]) -> list[str]:
        """
        将长期记忆整理为更适合 Prompt 注入的摘要列表

        说明：
        - 不直接把原始向量召回结果原样注入 Prompt，避免噪音和顺序混乱。
        - 按类型分组后输出，帮助导师模型快速理解“偏好 / 目标 / 误区 / 进展”。
        """
        type_labels = {
            "preference": "学习偏好",
            "goal": "当前目标",
            "misconception": "历史误区",
            "progress": "当前进展",
            "other": "其他记忆",
        }
        grouped_contents: dict[str, list[str]] = {
            "preference": [],
            "goal": [],
            "misconception": [],
            "progress": [],
            "other": [],
        }
        seen_contents: set[tuple[str, str]] = set()

        for fact in facts:
            key = (fact.memory_type, fact.content)
            if key in seen_contents:
                continue
            seen_contents.add(key)
            grouped_contents.setdefault(fact.memory_type, []).append(fact.content)

        summary_lines: list[str] = []
        ordered_types = [
            "preference",
            "goal",
            "misconception",
            "progress",
            "other",
        ]
        for memory_type in ordered_types:
            for content in grouped_contents.get(memory_type, []):
                label = type_labels.get(memory_type, "其他记忆")
                summary_lines.append(f"{label}：{content}")

        return summary_lines

    @staticmethod
    def build_long_term_memory_sections(facts: list[MentorMemoryFact]) -> dict[str, list[str]]:
        """
        将长期记忆拆分为固定小节

        这样 Prompt 可以稳定展示固定结构，而不是依赖模型自己从混合列表里再理解层次。
        """
        sections = {
            "preferences": [],
            "goals": [],
            "misconceptions": [],
            "progress": [],
            "other_facts": [],
        }
        seen_contents: set[tuple[str, str]] = set()

        for fact in facts:
            key = (fact.memory_type, fact.content)
            if key in seen_contents:
                continue
            seen_contents.add(key)

            if fact.memory_type == "preference":
                sections["preferences"].append(fact.content)
            elif fact.memory_type == "goal":
                sections["goals"].append(fact.content)
            elif fact.memory_type == "misconception":
                sections["misconceptions"].append(fact.content)
            elif fact.memory_type == "progress":
                sections["progress"].append(fact.content)
            else:
                sections["other_facts"].append(fact.content)

        return sections

    async def get_learning_context(
        self,
        db: AsyncSession,
        *,
        roadmap_id: str,
        concept_id: str | None = None,
    ) -> dict[str, str | None]:
        """
        获取路线图与教程上下文（内部会查询 roadmap，推荐已有 roadmap 对象时直接调用
        get_learning_context_from_roadmap 以避免重复查询）
        """
        roadmap = await self.roadmap_crud.get_by_roadmap_id(db, roadmap_id)
        return await self.get_learning_context_from_roadmap(
            db,
            roadmap=roadmap,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
        )

    async def get_learning_context_from_roadmap(
        self,
        db: AsyncSession,
        *,
        roadmap: object | None,
        roadmap_id: str,
        concept_id: str | None = None,
    ) -> dict[str, str | None]:
        """
        基于已预取的 roadmap 对象构建学习上下文，避免重复查询数据库

        相比 get_learning_context，此方法跳过 roadmap 查询步骤，
        适用于调用方已持有 roadmap 对象的场景（如并行 I/O 后复用）。
        """
        roadmap_context: str | None = None
        tutorial_excerpt: str | None = None
        concept_title: str | None = None

        if roadmap is not None:
            framework_data = getattr(roadmap, "framework_data", None) or {}
            title = framework_data.get("title") or getattr(roadmap, "title", None)
            roadmap_context = f"当前路线图：{title}"

            if concept_id:
                for stage in framework_data.get("stages", []):
                    for module in stage.get("modules", []):
                        for concept in module.get("concepts", []):
                            if concept.get("concept_id") == concept_id:
                                concept_title = concept.get("name")
                                if not tutorial_excerpt:
                                    tutorial_excerpt = concept.get("content_summary")
                                break

        if concept_id:
            tutorial = await self.tutorial_crud.get_latest_by_concept(db, roadmap_id, concept_id)
            if tutorial is not None:
                tutorial_excerpt = tutorial.summary
                if not concept_title:
                    concept_title = tutorial.title

        if tutorial_excerpt:
            tutorial_excerpt = tutorial_excerpt[: settings.MENTOR_CONTEXT_EXCERPT_MAX_LENGTH]

        return {
            "roadmap_context": roadmap_context,
            "tutorial_excerpt": tutorial_excerpt,
            "concept_title": concept_title,
        }


    async def get_learning_context_from_roadmap_cached(
        self,
        db: AsyncSession,
        *,
        roadmap: object | None,
        roadmap_id: str,
        concept_id: str | None,
    ) -> dict[str, str | None]:
        """
        基于已预取的 roadmap 构建学习上下文（优先命中预热缓存）

        与 get_learning_context_from_roadmap 相比，先检查 Redis 缓存；
        缓存未命中时使用传入的 roadmap 对象构建上下文，避免再次查询数据库。
        """
        cache_key = self.build_context_cache_key(roadmap_id, concept_id)
        try:
            await redis_client.connect()
            raw = await redis_client._client.get(cache_key)
            if raw:
                return fast_loads(raw)
        except Exception as exc:
            logger.warning("mentor_context_cache_read_failed", error=str(exc), cache_key=cache_key)

        # 缓存未命中：用已有的 roadmap 构建，不再查一次数据库
        return await self.get_learning_context_from_roadmap(
            db,
            roadmap=roadmap,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
        )

    async def get_learning_context_cached(
        self,
        db: AsyncSession,
        *,
        roadmap_id: str,
        concept_id: str | None,
    ) -> dict[str, str | None]:
        """
        获取学习上下文（优先命中预热缓存，未命中时查数据库并回写缓存）
        """
        cache_key = self.build_context_cache_key(roadmap_id, concept_id)

        try:
            await redis_client.connect()
            raw = await redis_client._client.get(cache_key)
            if raw:
                return fast_loads(raw)
        except Exception as exc:
            logger.warning("mentor_context_cache_read_failed", error=str(exc), cache_key=cache_key)

        # 缓存未命中：查数据库
        context = await self.get_learning_context(db, roadmap_id=roadmap_id, concept_id=concept_id)

        try:
            await redis_client.connect()
            await redis_client._client.setex(
                cache_key,
                settings.MENTOR_CONTEXT_CACHE_TTL_SECONDS,
                fast_dumps(context),
            )
        except Exception as exc:
            logger.warning("mentor_context_cache_write_failed", error=str(exc), cache_key=cache_key)

        return context

    async def warmup_context_cache(
        self,
        db: AsyncSession,
        *,
        roadmap_id: str,
        concept_id: str | None,
    ) -> dict[str, str | None]:
        """
        预热学习上下文缓存

        查询路线图和教程数据，写入 Redis，并返回上下文内容（供 warmup 接口记录日志）。
        """
        context = await self.get_learning_context(db, roadmap_id=roadmap_id, concept_id=concept_id)
        cache_key = self.build_context_cache_key(roadmap_id, concept_id)

        try:
            await redis_client.connect()
            await redis_client._client.setex(
                cache_key,
                settings.MENTOR_CONTEXT_CACHE_TTL_SECONDS,
                fast_dumps(context),
            )
        except Exception as exc:
            logger.warning("mentor_context_warmup_failed", error=str(exc), cache_key=cache_key)

        return context


mentor_context_service = MentorContextService()


def get_mentor_context_service() -> MentorContextService:
    """
    获取 AI 伴学助手上下文服务单例
    """
    return mentor_context_service
