"""
AI 伴学助手异步记忆任务
"""
import asyncio

import structlog
from sqlalchemy import func, select

from app.config.settings import settings
from app.core.celery_app import celery_app
from app.crud.crud_chat import chat_message_crud, chat_session_crud
from app.crud.crud_mentor_memory_job import mentor_memory_job_crud
from app.db.celery_session import get_celery_session
from app.models.database import ChatMessage, ChatSession
from app.services.learning.memory_service import get_memory_service
from app.services.learning.mentor_context_service import get_mentor_context_service
from app.tasks.event_loop_manager import run_async_in_worker_loop
from app.utils.idempotency import is_mentor_task_done, mark_mentor_task_done
from app.utils.redis_lock import redis_distributed_lock

logger = structlog.get_logger()


@celery_app.task(
    name="mentor.persist_and_extract_memory",
    bind=True,
    queue="mentor_persist",
    max_retries=3,
)
def persist_and_extract_memory_task(self, **payload) -> dict:
    """
    归档消息、更新短期记忆并派发长期记忆提炼任务
    """
    try:
        result = run_async_in_worker_loop(
            _persist_and_extract_memory_async(
                payload=payload,
                celery_task_id=self.request.id,
            )
        )
        return result
    except Exception as exc:
        logger.exception("mentor_persist_task_failed", error=str(exc), payload=payload)
        raise


@celery_app.task(
    name="mentor.extract_long_term_memory",
    bind=True,
    queue="mentor_memory",
    max_retries=5,
)
def extract_long_term_memory_task(self, **payload) -> dict:
    """
    提炼长期记忆
    """
    try:
        return run_async_in_worker_loop(
            _extract_long_term_memory_async(
                payload=payload,
                retry_count=self.request.retries,
            )
        )
    except Exception as exc:
        retry_count = int(self.request.retries or 0)
        is_dead_letter = retry_count >= int(self.max_retries or 0)

        run_async_in_worker_loop(
            _mark_memory_job_failed_async(
                job_id=payload["job_id"],
                last_error=str(exc),
                retry_count=retry_count + 1,
                dead_letter=is_dead_letter,
            )
        )

        if is_dead_letter:
            logger.exception("mentor_memory_task_dead_letter", error=str(exc), payload=payload)
            raise

        countdown = min(2 ** (retry_count + 1), 60)
        logger.warning(
            "mentor_memory_task_retrying",
            retry_count=retry_count + 1,
            countdown=countdown,
            error=str(exc),
        )
        raise self.retry(exc=exc, countdown=countdown)


@celery_app.task(
    name="mentor.run_reflection",
    bind=True,
    queue="mentor_memory",
    max_retries=3,
)
def run_mentor_reflection_task(self) -> dict:
    """
    长对话 reflection 定时任务
    """
    try:
        return run_async_in_worker_loop(_run_reflection_async())
    except Exception as exc:
        logger.exception("mentor_reflection_task_failed", error=str(exc))
        raise


async def _persist_and_extract_memory_async(
    *,
    payload: dict,
    celery_task_id: str | None,
) -> dict:
    """
    持久化消息并派发长期记忆任务
    """
    context_service = get_mentor_context_service()

    async with get_celery_session() as session:
        job = await mentor_memory_job_crud.get_by_job_id(session, payload["job_id"])
        if job is None:
            job = await mentor_memory_job_crud.create_job(
                session,
                job_id=payload["job_id"],
                message_id=payload["message_id"],
                user_id=payload["user_id"],
                session_id=payload["session_id"],
                payload=payload,
                celery_task_id=celery_task_id,
            )

        await mentor_memory_job_crud.mark_processing(
            session,
            job_id=job.job_id,
            celery_task_id=celery_task_id,
            retry_count=job.retry_count,
        )

        chat_session = await chat_session_crud.get_by_id(session, payload["session_id"])
        if chat_session is None:
            await chat_session_crud.create(
                session,
                obj_in={
                    "session_id": payload["session_id"],
                    "user_id": payload["user_id"],
                    "roadmap_id": payload["roadmap_id"],
                    "concept_id": payload.get("concept_id"),
                    "title": (payload.get("context") or {}).get("concept_title")
                    or payload["user_message"][:20],
                    "agent_type": payload["agent_type"],
                    "model_id": payload["model_id"],
                },
            )

        user_message = await chat_message_crud.get(session, payload["message_id"])
        if user_message is None:
            await chat_message_crud.create_message(
                session,
                message_id=payload["message_id"],
                session_id=payload["session_id"],
                role="user",
                content=payload["user_message"],
                agent_type=payload["agent_type"],
                model_id=payload["model_id"],
                trace_id=payload["trace_id"],
                message_metadata={
                    "roadmap_id": payload["roadmap_id"],
                    "concept_id": payload.get("concept_id"),
                },
            )

        assistant_message = await chat_message_crud.get(session, payload["assistant_message_id"])
        if assistant_message is None:
            await chat_message_crud.create_message(
                session,
                message_id=payload["assistant_message_id"],
                session_id=payload["session_id"],
                role="assistant",
                content=payload["assistant_message"],
                agent_type=payload["agent_type"],
                model_id=payload["model_id"],
                trace_id=payload["trace_id"],
                message_metadata={
                    "roadmap_id": payload["roadmap_id"],
                    "concept_id": payload.get("concept_id"),
                },
            )

        message_count = await chat_message_crud.count_by_session(session, payload["session_id"])
        await chat_session_crud.update_metadata(
            session,
            payload["session_id"],
            message_count=message_count,
            last_message_preview=payload["assistant_message"][:120],
            model_id=payload["model_id"],
            agent_type=payload["agent_type"],
        )

    await context_service.append_short_term_messages(
        session_id=payload["session_id"],
        messages=[
            {
                "message_id": payload["message_id"],
                "role": "user",
                "content": payload["user_message"],
            },
            {
                "message_id": payload["assistant_message_id"],
                "role": "assistant",
                "content": payload["assistant_message"],
            },
        ],
    )

    if not settings.MEM0_ENABLED:
        async with get_celery_session() as session:
            await mentor_memory_job_crud.mark_succeeded(session, job_id=payload["job_id"])
        return {
            "success": True,
            "job_id": payload["job_id"],
            "long_term_memory_skipped": True,
        }

    # celery_app.send_task 是同步阻塞调用，在 async 协程中直接调用会阻塞事件循环线程，
    # 导致所有后续任务永远无法被处理。必须通过 run_in_executor 在线程池中执行。
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(
        None,
        lambda: celery_app.send_task("mentor.extract_long_term_memory", kwargs=payload),
    )
    return {"success": True, "job_id": payload["job_id"]}


async def _extract_long_term_memory_async(*, payload: dict, retry_count: int) -> dict:
    """
    执行长期记忆提炼
    """
    if not settings.MEM0_ENABLED:
        async with get_celery_session() as session:
            await mentor_memory_job_crud.mark_succeeded(session, job_id=payload["job_id"])
        return {"success": True, "job_id": payload["job_id"], "skipped": True}

    if await is_mentor_task_done(payload["message_id"]):
        async with get_celery_session() as session:
            await mentor_memory_job_crud.mark_succeeded(session, job_id=payload["job_id"])
        return {"success": True, "skipped": True}

    lock_handle = await redis_distributed_lock.acquire(
        f"mentor:lock:memory:{payload['user_id']}",
        timeout_seconds=settings.MENTOR_MEMORY_LOCK_TIMEOUT_SECONDS,
        retry_seconds=settings.MENTOR_MEMORY_LOCK_RETRY_SECONDS,
        max_wait_seconds=5.0,
    )

    try:
        async with get_celery_session() as session:
            await mentor_memory_job_crud.mark_processing(
                session,
                job_id=payload["job_id"],
                retry_count=retry_count,
            )

        memory_service = get_memory_service()
        result = await memory_service.add_memory(
            user_id=payload["user_id"],
            messages=[
                {"role": "user", "content": payload["user_message"]},
                {"role": "assistant", "content": payload["assistant_message"]},
            ],
            metadata={
                "source": "mentor_chat",
                "session_id": payload["session_id"],
                "roadmap_id": payload["roadmap_id"],
                "concept_id": payload.get("concept_id"),
                "trace_id": payload["trace_id"],
            },
        )
        if not result.get("success"):
            raise RuntimeError(result.get("error") or "Mem0 写入失败")

        await mark_mentor_task_done(payload["message_id"])
        async with get_celery_session() as session:
            await mentor_memory_job_crud.mark_succeeded(session, job_id=payload["job_id"])

        # 新记忆已写入 Mem0，使该用户在当前 scope 下的 LTM 预热缓存失效，
        # 确保下次对话触发 warmup 时能拿到最新记忆
        try:
            context_service = get_mentor_context_service()
            await context_service.invalidate_ltm_cache(
                user_id=payload["user_id"],
                roadmap_id=payload["roadmap_id"],
                concept_id=payload.get("concept_id"),
            )
        except Exception as exc:
            logger.warning("mentor_ltm_cache_invalidate_failed_in_task", error=str(exc))

        return {"success": True, "job_id": payload["job_id"]}
    finally:
        await redis_distributed_lock.release(lock_handle)


async def _mark_memory_job_failed_async(
    *,
    job_id: str,
    last_error: str,
    retry_count: int,
    dead_letter: bool,
) -> None:
    """
    标记任务失败
    """
    async with get_celery_session() as session:
        await mentor_memory_job_crud.mark_failed(
            session,
            job_id=job_id,
            last_error=last_error,
            retry_count=retry_count,
            dead_letter=dead_letter,
        )


async def _run_reflection_async() -> dict:
    """
    执行长对话 reflection
    """
    memory_service = get_memory_service()

    async with get_celery_session() as session:
        result = await session.execute(
            select(
                ChatSession.session_id,
                ChatSession.user_id,
                ChatSession.roadmap_id,
                ChatSession.concept_id,
                func.count(ChatMessage.message_id).label("message_count"),
            )
            .join(ChatMessage, ChatMessage.session_id == ChatSession.session_id)
            .group_by(
                ChatSession.session_id,
                ChatSession.user_id,
                ChatSession.roadmap_id,
                ChatSession.concept_id,
            )
            .having(func.count(ChatMessage.message_id) >= settings.MENTOR_REFLECTION_MIN_MESSAGES)
        )
        candidates = result.all()

        reflection_results: list[dict] = []
        for candidate in candidates:
            messages = await chat_message_crud.get_recent_messages(
                session,
                candidate.session_id,
                limit=settings.MENTOR_STM_WINDOW_SIZE,
            )
            if not messages:
                continue

            condensed_messages = [
                {"role": item.role, "content": item.content}
                for item in messages[-10:]
            ]
            memory_result = await memory_service.add_memory(
                user_id=candidate.user_id,
                messages=condensed_messages,
                metadata={
                    "source": "mentor_reflection",
                    "session_id": candidate.session_id,
                    "roadmap_id": candidate.roadmap_id,
                    "concept_id": candidate.concept_id,
                },
            )
            reflection_results.append(
                {
                    "session_id": candidate.session_id,
                    "message_count": candidate.message_count,
                    "success": memory_result.get("success", False),
                }
            )

    return {
        "success": True,
        "processed_count": len(reflection_results),
        "results": reflection_results,
    }
