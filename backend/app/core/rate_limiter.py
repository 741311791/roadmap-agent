"""
全局API速率限制器

基于滑动窗口算法，使用Redis存储请求时间戳，支持多种API Provider的独立速率限制。
防止超过API厂商的IP级别速率限制（RPM - Requests Per Minute）。

设计原则：
- 全局单例：同一Provider共享速率限制（因为厂商按IP限制）
- 滑动窗口：精确控制每分钟请求数
- 优雅等待：超限时自动等待，而非直接拒绝
- 可观测性：记录等待日志，提供统计接口
"""
import asyncio
import time
from typing import Dict, Any
import structlog

from app.db.redis_client import get_redis_client
from app.config.settings import settings

logger = structlog.get_logger()


class APIRateLimiter:
    """
    API速率限制器
    
    使用滑动窗口算法控制API调用速率，防止超过厂商的RPM限制。
    
    工作原理：
    1. 使用Redis ZSET存储请求时间戳（score=timestamp, value=unique_id）
    2. 请求前检查：清理1分钟前的记录，统计当前窗口内的请求数
    3. 如果未超限：记录本次请求，允许通过
    4. 如果超限：计算需要等待的时间，sleep后重试
    
    Redis Key格式：
    - rate_limit:{provider} (如: rate_limit:openai, rate_limit:anthropic)
    
    支持的Provider：
    - openai: OpenAI API (GPT-4, GPT-4o-mini等)
    - anthropic: Anthropic API (Claude系列)
    - deepseek: DeepSeek API
    - tavily: Tavily Search API
    """
    
    def __init__(self):
        """
        初始化速率限制器
        
        从settings中读取各Provider的RPM限制配置
        """
        self.redis_client = get_redis_client()
        
        # 从配置中读取各Provider的RPM限制
        self.rpm_limits: Dict[str, int] = {
            "openai": settings.OPENAI_RPM_LIMIT,
            "anthropic": settings.ANTHROPIC_RPM_LIMIT,
            "deepseek": settings.DEEPSEEK_RPM_LIMIT,
            "tavily": settings.TAVILY_RATE_LIMIT_PER_MINUTE,
        }
        
        # 统计信息（内存存储，用于监控）
        self.stats: Dict[str, Dict[str, Any]] = {
            provider: {
                "total_requests": 0,
                "total_waits": 0,
                "total_wait_seconds": 0.0,
            }
            for provider in self.rpm_limits.keys()
        }
        
        logger.info(
            "rate_limiter_initialized",
            rpm_limits=self.rpm_limits,
        )
    
    def _get_redis_key(self, provider: str) -> str:
        """
        获取Redis Key
        
        Args:
            provider: API提供商（如openai, anthropic）
            
        Returns:
            Redis Key字符串
        """
        return f"rate_limit:{provider.lower()}"
    
    async def acquire(self, provider: str) -> None:
        """
        获取API调用许可
        
        如果当前速率未超限，立即返回；
        如果超限，等待直到可以调用。
        
        Args:
            provider: API提供商（如openai, anthropic, deepseek, tavily）
            
        Raises:
            ValueError: 不支持的provider
        """
        provider = provider.lower()
        
        # 检查是否支持该provider
        if provider not in self.rpm_limits:
            logger.warning(
                "rate_limiter_unsupported_provider",
                provider=provider,
                supported=list(self.rpm_limits.keys()),
            )
            # 不支持的provider，不限制（优雅降级）
            return
        
        limit = self.rpm_limits[provider]
        redis_key = self._get_redis_key(provider)
        
        # 记录统计
        self.stats[provider]["total_requests"] += 1
        
        while True:
            now = time.time()
            window_start = now - 60  # 1分钟窗口
            
            try:
                # 确保Redis连接
                await self.redis_client.connect()
                
                # 1. 清理1分钟前的旧记录
                await self.redis_client._client.zremrangebyscore(
                    redis_key,
                    '-inf',
                    window_start
                )
                
                # 2. 统计当前窗口内的请求数
                current_count = await self.redis_client._client.zcard(redis_key)
                
                # 3. 检查是否超限
                if current_count < limit:
                    # 未超限，记录本次请求
                    request_id = f"{now}:{asyncio.current_task().get_name()}"
                    await self.redis_client._client.zadd(
                        redis_key,
                        {request_id: now}
                    )
                    
                    # 设置Key过期时间（70秒，略大于1分钟）
                    await self.redis_client._client.expire(redis_key, 70)
                    
                    logger.debug(
                        "rate_limiter_acquired",
                        provider=provider,
                        current_count=current_count + 1,
                        limit=limit,
                    )
                    
                    return  # 成功获取，返回
                
                else:
                    # 超限，计算需要等待的时间
                    # 获取窗口内最早的请求时间戳
                    oldest_requests = await self.redis_client._client.zrange(
                        redis_key,
                        0,
                        0,
                        withscores=True
                    )
                    
                    if oldest_requests:
                        oldest_timestamp = oldest_requests[0][1]
                        # 计算最早的请求何时会移出窗口（变成61秒前）
                        wait_time = max(0.1, oldest_timestamp + 60 - now + 0.5)
                    else:
                        # 理论上不会到这里，默认等待1秒
                        wait_time = 1.0
                    
                    # 记录等待统计
                    self.stats[provider]["total_waits"] += 1
                    self.stats[provider]["total_wait_seconds"] += wait_time
                    
                    logger.warning(
                        "rate_limiter_waiting",
                        provider=provider,
                        current_count=current_count,
                        limit=limit,
                        wait_seconds=round(wait_time, 2),
                    )
                    
                    # 等待
                    await asyncio.sleep(wait_time)
                    
                    # 重试（继续while循环）
            
            except Exception as e:
                logger.error(
                    "rate_limiter_error",
                    provider=provider,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                
                # 发生错误时，优雅降级：允许通过（避免阻塞业务）
                logger.warning(
                    "rate_limiter_degraded",
                    provider=provider,
                    message="速率限制器异常，降级处理：允许请求通过"
                )
                return
    
    async def get_current_usage(self, provider: str) -> Dict[str, Any]:
        """
        获取当前速率使用情况
        
        Args:
            provider: API提供商
            
        Returns:
            使用情况字典，包含：
            - current_count: 当前窗口内的请求数
            - limit: 速率限制
            - usage_percent: 使用率百分比
            - available: 剩余可用次数
        """
        provider = provider.lower()
        
        if provider not in self.rpm_limits:
            return {
                "provider": provider,
                "error": "unsupported provider"
            }
        
        limit = self.rpm_limits[provider]
        redis_key = self._get_redis_key(provider)
        
        try:
            await self.redis_client.connect()
            
            # 清理过期记录
            now = time.time()
            window_start = now - 60
            await self.redis_client._client.zremrangebyscore(
                redis_key,
                '-inf',
                window_start
            )
            
            # 统计当前请求数
            current_count = await self.redis_client._client.zcard(redis_key)
            
            return {
                "provider": provider,
                "current_count": current_count,
                "limit": limit,
                "usage_percent": round((current_count / limit) * 100, 2),
                "available": max(0, limit - current_count),
            }
        
        except Exception as e:
            logger.error(
                "rate_limiter_get_usage_error",
                provider=provider,
                error=str(e)
            )
            return {
                "provider": provider,
                "error": str(e)
            }
    
    async def get_all_usage(self) -> Dict[str, Any]:
        """
        获取所有Provider的速率使用情况
        
        Returns:
            包含所有Provider使用情况的字典
        """
        result = {}
        
        for provider in self.rpm_limits.keys():
            result[provider] = await self.get_current_usage(provider)
        
        return result
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        获取统计信息
        
        Returns:
            各Provider的统计信息（总请求数、等待次数、等待时长）
        """
        return self.stats.copy()
    
    async def reset_provider(self, provider: str) -> bool:
        """
        重置某个Provider的速率限制（清空窗口记录）
        
        Args:
            provider: API提供商
            
        Returns:
            是否成功
        """
        provider = provider.lower()
        
        if provider not in self.rpm_limits:
            return False
        
        redis_key = self._get_redis_key(provider)
        
        try:
            await self.redis_client.connect()
            await self.redis_client._client.delete(redis_key)
            
            logger.info(
                "rate_limiter_reset",
                provider=provider,
            )
            return True
        
        except Exception as e:
            logger.error(
                "rate_limiter_reset_error",
                provider=provider,
                error=str(e)
            )
            return False


# 全局单例
rate_limiter = APIRateLimiter()


def get_rate_limiter() -> APIRateLimiter:
    """
    获取全局速率限制器实例（用于依赖注入）
    
    Returns:
        APIRateLimiter 全局单例实例
    """
    return rate_limiter
