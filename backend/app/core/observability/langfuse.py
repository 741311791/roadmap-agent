"""
Langfuse 观测性统一封装
"""
from __future__ import annotations

import re
from contextlib import contextmanager, nullcontext
from functools import lru_cache
from typing import Any, Iterator

import structlog
from langfuse import Langfuse, propagate_attributes

from app.config.settings import settings

logger = structlog.get_logger()

SENSITIVE_KEY_PATTERN = re.compile(
    r"(api[_-]?key|authorization|cookie|token|secret|password|email|phone|mobile)",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+\.[A-Za-z0-9-.]+")
BEARER_PATTERN = re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)


def _mask_sensitive_data(*, data: Any, **_: Any) -> Any:
    """
    在上报 Langfuse 前对敏感数据做递归脱敏
    """
    if isinstance(data, dict):
        masked_dict: dict[str, Any] = {}
        for key, value in data.items():
            if SENSITIVE_KEY_PATTERN.search(str(key)):
                masked_dict[str(key)] = "[REDACTED]"
                continue
            masked_dict[str(key)] = _mask_sensitive_data(data=value)
        return masked_dict

    if isinstance(data, list):
        return [_mask_sensitive_data(data=item) for item in data]

    if isinstance(data, tuple):
        return [_mask_sensitive_data(data=item) for item in data]

    if isinstance(data, str):
        masked_text = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", data)
        masked_text = BEARER_PATTERN.sub("Bearer [TOKEN_REDACTED]", masked_text)
        return masked_text

    return data


def is_langfuse_enabled() -> bool:
    """
    判断当前环境是否启用 Langfuse
    """
    return bool(
        settings.LANGFUSE_ENABLED
        and (settings.LANGFUSE_PUBLIC_KEY or "").strip()
        and (settings.LANGFUSE_SECRET_KEY or "").strip()
    )


@lru_cache(maxsize=1)
def get_langfuse_client() -> Langfuse | None:
    """
    获取 Langfuse 单例客户端
    """
    if not is_langfuse_enabled():
        logger.info("langfuse_disabled")
        return None

    client = Langfuse(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        base_url=settings.LANGFUSE_BASE_URL,
        debug=settings.LANGFUSE_DEBUG,
        environment=settings.ENVIRONMENT,
        sample_rate=settings.LANGFUSE_SAMPLE_RATE,
        release="1.0.0",
        mask=_mask_sensitive_data,
    )
    logger.info(
        "langfuse_initialized",
        base_url=settings.LANGFUSE_BASE_URL,
        environment=settings.ENVIRONMENT,
        sample_rate=settings.LANGFUSE_SAMPLE_RATE,
    )
    return client


def create_langfuse_trace_id(seed: str | None = None) -> str:
    """
    生成 Langfuse 兼容的 Trace ID
    """
    client = get_langfuse_client()
    if client is not None:
        return client.create_trace_id(seed=seed)
    return Langfuse.create_trace_id(seed=seed)


def build_mentor_trace_metadata(
    *,
    external_trace_id: str,
    user_id: str | None = None,
    session_id: str | None = None,
    roadmap_id: str | None = None,
    concept_id: str | None = None,
    agent_id: str | None = None,
    agent_type: str | None = None,
    model: str | None = None,
    provider: str | None = None,
    assist_mode: str | None = None,
    resolved_assist_mode: str | None = None,
    prompt_template: str | None = None,
    celery_task_id: str | None = None,
    queue_name: str | None = None,
    job_id: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    构建 Mentor 链路的统一 metadata
    """
    metadata = {
        "external_trace_id": external_trace_id,
        "user_id": user_id,
        "session_id": session_id,
        "roadmap_id": roadmap_id,
        "concept_id": concept_id,
        "agent_id": agent_id,
        "agent_type": agent_type,
        "model": model,
        "provider": provider,
        "assist_mode": assist_mode,
        "resolved_assist_mode": resolved_assist_mode,
        "prompt_template": prompt_template,
        "celery_task_id": celery_task_id,
        "queue_name": queue_name,
        "job_id": job_id,
        "environment": settings.ENVIRONMENT,
        "app_version": "1.0.0",
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    return {
        key: value
        for key, value in metadata.items()
        if value is not None
    }


@contextmanager
def propagate_mentor_attributes(
    *,
    user_id: str | None,
    session_id: str | None,
    trace_name: str,
    metadata: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> Iterator[None]:
    """
    传播 Mentor 链路的 Trace 属性
    """
    if get_langfuse_client() is None:
        with nullcontext():
            yield
        return

    normalized_metadata = {
        key: str(value)
        for key, value in (metadata or {}).items()
        if value is not None
    }
    with propagate_attributes(
        user_id=user_id,
        session_id=session_id,
        metadata=normalized_metadata or None,
        tags=tags,
        trace_name=trace_name,
    ):
        yield


@contextmanager
def start_langfuse_observation(
    *,
    name: str,
    as_type: str = "span",
    trace_id: str | None = None,
    input: Any | None = None,
    output: Any | None = None,
    metadata: dict[str, Any] | None = None,
    model: str | None = None,
    model_parameters: dict[str, Any] | None = None,
    completion_start_time: Any | None = None,
) -> Iterator[Any | None]:
    """
    启动一个 Langfuse Observation；未启用时自动退化为 no-op
    """
    client = get_langfuse_client()
    if client is None:
        with nullcontext():
            yield None
        return

    trace_context = {"trace_id": trace_id} if trace_id else None
    with client.start_as_current_observation(
        trace_context=trace_context,
        name=name,
        as_type=as_type,
        input=input,
        output=output,
        metadata=metadata,
        model=model,
        model_parameters=model_parameters,
        completion_start_time=completion_start_time,
    ) as observation:
        yield observation


def update_current_generation_safely(**kwargs: Any) -> None:
    """
    安全更新当前 generation，避免观测失败影响主链路
    """
    client = get_langfuse_client()
    if client is None:
        return

    try:
        client.update_current_generation(
            **{key: value for key, value in kwargs.items() if value is not None}
        )
    except Exception as exc:
        logger.debug("langfuse_update_current_generation_failed", error=str(exc))


def update_current_span_safely(**kwargs: Any) -> None:
    """
    安全更新当前 span，避免观测失败影响主链路
    """
    client = get_langfuse_client()
    if client is None:
        return

    try:
        client.update_current_span(
            **{key: value for key, value in kwargs.items() if value is not None}
        )
    except Exception as exc:
        logger.debug("langfuse_update_current_span_failed", error=str(exc))


def flush_langfuse() -> None:
    """
    在明确边界处刷新 Langfuse 缓冲
    """
    client = get_langfuse_client()
    if client is None:
        return

    try:
        client.flush()
    except Exception as exc:
        logger.warning("langfuse_flush_failed", error=str(exc))
