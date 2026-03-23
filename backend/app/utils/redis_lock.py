"""
Redis 分布式锁工具
"""
import asyncio
import uuid
from dataclasses import dataclass

import structlog

from app.db.redis_client import redis_client

logger = structlog.get_logger()


@dataclass(slots=True)
class RedisLockHandle:
    """
    Redis 锁句柄
    """
    key: str
    value: str


class RedisDistributedLock:
    """
    Redis 分布式锁

    使用随机 token 作为锁值，释放时校验归属，避免误删其他进程持有的锁。
    """

    RELEASE_SCRIPT = """
    if redis.call("GET", KEYS[1]) == ARGV[1] then
        return redis.call("DEL", KEYS[1])
    end
    return 0
    """

    async def acquire(
        self,
        key: str,
        *,
        timeout_seconds: int,
        retry_seconds: float = 0.2,
        max_wait_seconds: float | None = None,
    ) -> RedisLockHandle:
        """
        获取 Redis 锁

        Args:
            key: 锁 Key
            timeout_seconds: 锁 TTL
            retry_seconds: 重试间隔
            max_wait_seconds: 最长等待时间；为空表示一直等待

        Returns:
            锁句柄

        Raises:
            TimeoutError: 超过等待时间仍未获取到锁
        """
        await redis_client.connect()
        lock_value = str(uuid.uuid4())
        elapsed = 0.0

        while True:
            acquired = await redis_client._client.set(
                key,
                lock_value,
                nx=True,
                ex=timeout_seconds,
            )
            if acquired:
                logger.info("redis_lock_acquired", key=key)
                return RedisLockHandle(key=key, value=lock_value)

            if max_wait_seconds is not None and elapsed >= max_wait_seconds:
                raise TimeoutError(f"获取锁超时: {key}")

            await asyncio.sleep(retry_seconds)
            elapsed += retry_seconds

    async def release(self, handle: RedisLockHandle) -> bool:
        """
        释放 Redis 锁
        """
        await redis_client.connect()
        result = await redis_client._client.eval(
            self.RELEASE_SCRIPT,
            1,
            handle.key,
            handle.value,
        )
        released = bool(result)
        if released:
            logger.info("redis_lock_released", key=handle.key)
        return released

    async def extend(self, handle: RedisLockHandle, timeout_seconds: int) -> bool:
        """
        续约 Redis 锁
        """
        await redis_client.connect()
        current_value = await redis_client._client.get(handle.key)
        if current_value != handle.value:
            return False
        await redis_client._client.expire(handle.key, timeout_seconds)
        return True


redis_distributed_lock = RedisDistributedLock()
