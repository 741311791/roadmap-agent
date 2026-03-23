"""
AI 伴学助手限流服务
"""
import structlog

from app.config.settings import settings
from app.db.redis_client import redis_client

logger = structlog.get_logger()


class MentorRateLimitService:
    """
    AI 伴学助手限流服务
    """

    async def check_rate_limit(
        self,
        *,
        user_id: str,
        ip: str | None,
    ) -> None:
        """
        检查用户和 IP 限流

        Raises:
            ValueError: 超过限流阈值
        """
        await self._check_key(
            key=f"mentor:ratelimit:user:{user_id}",
            limit=settings.MENTOR_RATE_LIMIT_PER_MINUTE,
        )

        if ip:
            await self._check_key(
                key=f"mentor:ratelimit:ip:{ip}",
                limit=settings.MENTOR_IP_RATE_LIMIT_PER_MINUTE,
            )

    async def _check_key(self, *, key: str, limit: int) -> None:
        """
        检查单个限流 Key
        """
        await redis_client.connect()
        current_value = await redis_client._client.incr(key)
        if current_value == 1:
            await redis_client._client.expire(key, 60)

        if current_value > limit:
            logger.warning("mentor_rate_limit_exceeded", redis_key=key, limit=limit)
            raise ValueError("请求过于频繁，请稍后再试")


mentor_rate_limit_service = MentorRateLimitService()


def get_mentor_rate_limit_service() -> MentorRateLimitService:
    """
    获取 AI 伴学助手限流服务单例
    """
    return mentor_rate_limit_service
