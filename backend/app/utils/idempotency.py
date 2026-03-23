"""
异步任务幂等工具
"""
import structlog

from app.config.settings import settings
from app.db.redis_client import redis_client

logger = structlog.get_logger()


def build_mentor_task_done_key(message_id: str) -> str:
    """
    构建 AI 伴学助手异步任务完成标记 Key
    """
    return f"mentor:task_done:{message_id}"


async def is_mentor_task_done(message_id: str) -> bool:
    """
    检查 AI 伴学助手异步任务是否已完成
    """
    key = build_mentor_task_done_key(message_id)
    return await redis_client.exists(key)


async def mark_mentor_task_done(message_id: str) -> None:
    """
    标记 AI 伴学助手异步任务已完成
    """
    key = build_mentor_task_done_key(message_id)
    await redis_client.connect()
    await redis_client._client.set(key, "1", ex=settings.MENTOR_TASK_DONE_TTL_SECONDS)
    logger.info("mentor_task_marked_done", message_id=message_id, redis_key=key)
