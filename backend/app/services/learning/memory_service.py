"""
AI 伴学助手长期记忆服务
"""
import asyncio
from functools import cached_property
from typing import Any
from urllib.parse import quote, unquote

import structlog
from pydantic import BaseModel, Field

from app.config.settings import settings

logger = structlog.get_logger()


class MentorMemoryFact(BaseModel):
    """
    长期记忆检索结果
    """
    memory_id: str | None = Field(None, description="记忆 ID")
    memory_type: str = Field("other", description="记忆类型")
    content: str = Field(..., description="记忆内容")
    score: float | None = Field(None, description="召回分数")
    metadata: dict[str, Any] = Field(default_factory=dict, description="附加元数据")


class MemoryService:
    """
    AI 伴学助手长期记忆服务

    说明：
    - 优先尝试接入 Mem0。
    - 若运行环境未安装或未启用 Mem0，则自动降级为 no-op，
      这样不会影响主链路可用性。
    """

    def __init__(self) -> None:
        self._memory_client: Any | None = None

    @cached_property
    def _mem0_module(self) -> Any | None:
        """
        延迟加载 Mem0 模块
        """
        if not settings.MEM0_ENABLED:
            return None

        try:
            from mem0 import Memory  # type: ignore

            return Memory
        except Exception as exc:  # pragma: no cover - 依赖缺失时走降级逻辑
            logger.warning("mem0_import_failed", error=str(exc))
            return None

    def _build_mem0_config(self) -> dict[str, Any] | None:
        """
        构建 Mem0 配置

        运行参数来自环境变量，长期记忆 Prompt 统一从 backend/prompts 目录读取。
        """
        config = settings.get_mem0_config
        if not config:
            return None

        vector_store = config.setdefault("vector_store", {})
        vector_config = vector_store.setdefault("config", {})
        if "database_url" in vector_config and "connection_string" not in vector_config:
            vector_config["connection_string"] = vector_config.pop("database_url")
        if "connection_string" in vector_config:
            vector_config["connection_string"] = self._normalize_postgres_connection_string(
                str(vector_config["connection_string"])
            )
        vector_config.setdefault("collection_name", settings.MEM0_LTM_COLLECTION_NAME)
        return config

    @staticmethod
    def _normalize_postgres_connection_string(connection_string: str) -> str:
        """
        标准化 PostgreSQL 连接串

        说明：
        - Mem0 的 PgVector 配置要求使用 `connection_string`。
        - 若密码中包含 `#` 等特殊字符，需要进行 URL 编码，否则会被当作 fragment。
        """
        if "://" not in connection_string or "@" not in connection_string:
            return connection_string

        scheme, remainder = connection_string.split("://", 1)
        credentials, separator, suffix = remainder.rpartition("@")
        if not separator or ":" not in credentials:
            return connection_string

        username, password = credentials.split(":", 1)
        normalized_username = quote(unquote(username), safe="")
        normalized_password = quote(unquote(password), safe="")
        return f"{scheme}://{normalized_username}:{normalized_password}@{suffix}"

    def _get_client(self) -> Any | None:
        """
        获取 Mem0 客户端实例
        """
        if self._memory_client is not None:
            return self._memory_client

        memory_cls = self._mem0_module
        if memory_cls is None:
            return None

        self._patch_mem0_openai_embedder()
        try:
            config = self._build_mem0_config()
            if config:
                self._memory_client = memory_cls.from_config(config)
            else:
                self._memory_client = memory_cls()
            logger.info("mem0_client_initialized", has_custom_config=bool(config))
            return self._memory_client
        except Exception as exc:  # pragma: no cover - 依赖或配置异常
            logger.warning("mem0_client_init_failed", error=str(exc))
            return None

    @staticmethod
    def _patch_mem0_openai_embedder() -> None:
        """
        修补 Mem0 的 OpenAI Embedding 调用

        说明：
        - 当前安装的 Mem0 版本会固定传 `dimensions`。
        - 某些 OpenAI 兼容网关会拒绝该参数。
        - 这里保留原始调用；若命中该类报错，则自动重试一次并去掉 `dimensions`。
        """
        try:
            from mem0.embeddings.openai import OpenAIEmbedding  # type: ignore
        except Exception:
            return

        if getattr(OpenAIEmbedding, "_roadmap_dimensions_patch_applied", False):
            return

        def patched_embed(instance: Any, text: str, memory_action: str | None = None) -> list[float]:
            normalized_text = text.replace("\n", " ")
            try:
                return (
                    instance.client.embeddings.create(
                        input=[normalized_text],
                        model=instance.config.model,
                        dimensions=instance.config.embedding_dims,
                        encoding_format="float",
                    )
                    .data[0]
                    .embedding
                )
            except Exception as exc:
                if "dimensions" not in str(exc):
                    raise

                logger.warning(
                    "mem0_embedding_retry_without_dimensions",
                    model=getattr(instance.config, "model", None),
                    error=str(exc),
                )
                return (
                    instance.client.embeddings.create(
                        input=[normalized_text],
                        model=instance.config.model,
                        encoding_format="float",
                    )
                    .data[0]
                    .embedding
                )

        OpenAIEmbedding.embed = patched_embed
        OpenAIEmbedding._roadmap_dimensions_patch_applied = True

    @staticmethod
    def parse_memory_content(content: str) -> tuple[str, str]:
        """
        解析长期记忆文本中的类型标签

        支持两类来源：
        1. 新版 prompt 生成的显式标签，如 `[preference] ...`
        2. 历史数据的启发式推断，避免旧记忆失去分类能力
        """
        normalized_content = content.strip()
        tagged_prefixes = {
            "[preference]": "preference",
            "[goal]": "goal",
            "[misconception]": "misconception",
            "[progress]": "progress",
        }
        for prefix, memory_type in tagged_prefixes.items():
            if normalized_content.startswith(prefix):
                return memory_type, normalized_content[len(prefix):].strip()

        if "偏好" in normalized_content or "更希望" in normalized_content:
            return "preference", normalized_content
        if "目标" in normalized_content or "计划" in normalized_content:
            return "goal", normalized_content
        if "混淆" in normalized_content or "误区" in normalized_content or "薄弱点" in normalized_content:
            return "misconception", normalized_content
        if "已经能" in normalized_content or "已掌握" in normalized_content or "值得定期复习" in normalized_content:
            return "progress", normalized_content
        return "other", normalized_content

    async def search_memories(
        self,
        *,
        query: str,
        user_id: str,
        limit: int | None = None,
    ) -> list[MentorMemoryFact]:
        """
        检索长期记忆
        """
        client = self._get_client()
        if client is None:
            return []

        top_k = limit or settings.MENTOR_LTM_TOP_K

        def _search() -> list[MentorMemoryFact]:
            try:
                result = client.search(
                    query,
                    user_id=user_id,
                    filters={"user_id": user_id},
                    limit=top_k,
                )
            except TypeError:
                try:
                    result = client.search(
                        query,
                        user_id=user_id,
                        filters={"user_id": user_id},
                        top_k=top_k,
                    )
                except TypeError:
                    result = client.search(
                        query,
                        user_id=user_id,
                        filters={"user_id": user_id},
                    )
            raw_results = result.get("results", []) if isinstance(result, dict) else []
            facts: list[MentorMemoryFact] = []
            for item in raw_results:
                content = item.get("memory") or item.get("text") or ""
                if not content:
                    continue
                memory_type, normalized_content = self.parse_memory_content(content)
                facts.append(
                    MentorMemoryFact(
                        memory_id=item.get("id"),
                        memory_type=memory_type,
                        content=normalized_content,
                        score=item.get("score"),
                        metadata={
                            key: value
                            for key, value in item.items()
                            if key not in {"id", "memory", "text", "score"}
                        },
                    )
                )
            return facts

        try:
            return await asyncio.to_thread(_search)
        except Exception as exc:
            logger.warning("mem0_search_failed", error=str(exc), user_id=user_id)
            return []

    async def add_memory(
        self,
        *,
        user_id: str,
        messages: list[dict[str, str]],
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        添加长期记忆
        """
        client = self._get_client()
        if client is None:
            return {"enabled": False, "success": False}

        def _add() -> dict[str, Any]:
            kwargs: dict[str, Any] = {"user_id": user_id}
            if metadata:
                kwargs["metadata"] = metadata
            result = client.add(messages, **kwargs)
            if isinstance(result, dict):
                return result
            return {"result": result}

        try:
            result = await asyncio.to_thread(_add)
            result.setdefault("enabled", True)
            result.setdefault("success", True)
            return result
        except Exception as exc:
            logger.warning("mem0_add_failed", error=str(exc), user_id=user_id)
            return {"enabled": True, "success": False, "error": str(exc)}


memory_service = MemoryService()


def get_memory_service() -> MemoryService:
    """
    获取长期记忆服务单例
    """
    return memory_service
