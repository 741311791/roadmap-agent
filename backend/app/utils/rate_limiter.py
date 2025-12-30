"""
全局速率限制器（支持多进程/多线程）

使用场景：
- Tavily API 限制（每分钟 100 次）
- 其他外部 API 调用限制

设计原则：
- 基于 Redis 实现，支持多进程/多线程共享状态
- 使用滑动窗口算法，精确控制速率
- 自动清理过期记录，避免内存泄漏
"""
import time
import asyncio
from typing import Optional
import structlog
from redis.asyncio import Redis
from app.config.settings import settings

logger = structlog.get_logger()


class GlobalRateLimiter:
    """
    全局速率限制器（基于 Redis）
    
    特性：
    - 使用 Redis Sorted Set 实现滑动窗口
    - 支持多进程/多线程安全
    - 自动清理过期记录
    - 原子操作，避免竞态条件
    """
    
    def __init__(
        self,
        redis_client: Redis,
        key_prefix: str,
        max_requests: int,
        window_seconds: int,
    ):
        """
        初始化速率限制器
        
        Args:
            redis_client: Redis 客户端
            key_prefix: Redis key 前缀（用于区分不同的限制器）
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口大小（秒）
        """
        self.redis = redis_client
        self.key = f"rate_limiter:{key_prefix}"
        self.max_requests = max_requests
        self.window_seconds = window_seconds
    
    async def acquire(self, timeout: Optional[float] = None) -> bool:
        """
        获取执行许可（等待直到有可用配额）
        
        Args:
            timeout: 最大等待时间（秒），None 表示无限等待
            
        Returns:
            True 如果成功获取许可
            
        Raises:
            TimeoutError: 超时未获取到许可
        """
        start_time = time.time()
        
        while True:
            # 尝试获取许可
            allowed = await self._try_acquire()
            
            if allowed:
                return True
            
            # 检查超时
            if timeout is not None and (time.time() - start_time) >= timeout:
                raise TimeoutError(
                    f"Rate limiter timeout after {timeout}s "
                    f"(max {self.max_requests} requests per {self.window_seconds}s)"
                )
            
            # 计算需要等待的时间
            wait_time = await self._calculate_wait_time()
            
            logger.debug(
                "rate_limiter_waiting",
                key=self.key,
                wait_seconds=round(wait_time, 2),
                max_requests=self.max_requests,
                window_seconds=self.window_seconds,
            )
            
            # 等待后重试
            await asyncio.sleep(wait_time)
    
    async def _try_acquire(self) -> bool:
        """
        尝试获取执行许可（非阻塞）
        
        Returns:
            True 如果成功获取许可，False 如果超过限制
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Redis Pipeline（原子操作）
        pipe = self.redis.pipeline()
        
        # 1. 删除过期的记录
        pipe.zremrangebyscore(self.key, 0, window_start)
        
        # 2. 获取当前窗口内的请求数
        pipe.zcard(self.key)
        
        # 执行 pipeline
        results = await pipe.execute()
        current_count = results[1]  # zcard 的结果
        
        # 检查是否超过限制
        if current_count >= self.max_requests:
            logger.debug(
                "rate_limiter_throttled",
                key=self.key,
                current_count=current_count,
                max_requests=self.max_requests,
            )
            return False
        
        # 记录新请求（使用当前时间戳作为 score 和 value）
        await self.redis.zadd(self.key, {str(now): now})
        
        # 设置过期时间（防止 key 永久存在）
        await self.redis.expire(self.key, self.window_seconds * 2)
        
        logger.debug(
            "rate_limiter_acquired",
            key=self.key,
            current_count=current_count + 1,
            max_requests=self.max_requests,
        )
        
        return True
    
    async def _calculate_wait_time(self) -> float:
        """
        计算需要等待的时间（直到有新的配额可用）
        
        Returns:
            等待时间（秒）
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # 获取窗口内最旧的请求时间
        oldest_requests = await self.redis.zrangebyscore(
            self.key,
            window_start,
            now,
            start=0,
            num=1,
            withscores=True,
        )
        
        if not oldest_requests:
            # 没有请求记录，立即可用
            return 0.1
        
        # 计算最旧请求何时过期
        oldest_timestamp = float(oldest_requests[0][1])
        expire_time = oldest_timestamp + self.window_seconds
        wait_time = expire_time - now
        
        # 最少等待 0.1 秒
        return max(0.1, wait_time)
    
    async def get_current_count(self) -> int:
        """
        获取当前窗口内的请求数
        
        Returns:
            请求数
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # 清理过期记录
        await self.redis.zremrangebyscore(self.key, 0, window_start)
        
        # 获取当前计数
        count = await self.redis.zcard(self.key)
        return count
    
    async def reset(self):
        """重置限制器（清空所有记录）"""
        await self.redis.delete(self.key)
        logger.info("rate_limiter_reset", key=self.key)


# ============================================================
# 全局 Tavily API 速率限制器工厂
# ============================================================

_tavily_rate_limiter: Optional[GlobalRateLimiter] = None


async def get_tavily_rate_limiter() -> GlobalRateLimiter:
    """
    获取全局 Tavily API 速率限制器单例
    
    限制：每分钟最多 100 次请求
    
    Returns:
        GlobalRateLimiter 实例
    """
    global _tavily_rate_limiter
    
    if _tavily_rate_limiter is None:
        from redis.asyncio import from_url
        
        # 创建 Redis 客户端
        redis_client = from_url(
            settings.get_redis_url,
            encoding="utf-8",
            decode_responses=False,
        )
        
        # 创建限制器（每分钟 100 次）
        _tavily_rate_limiter = GlobalRateLimiter(
            redis_client=redis_client,
            key_prefix="tavily_api",
            max_requests=100,
            window_seconds=60,
        )
        
        logger.info(
            "tavily_rate_limiter_initialized",
            max_requests=100,
            window_seconds=60,
        )
    
    return _tavily_rate_limiter

