"""
Redis 客户端封装
"""
from typing import Any
import json
import redis.asyncio as aioredis
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class RedisClient:
    """Redis 异步客户端封装"""
    
    def __init__(self):
        self._client: aioredis.Redis | None = None
    
    async def connect(self):
        """
        建立连接
        
        支持标准 Redis 和 Upstash Redis（通过 rediss:// 协议使用 TLS/SSL）
        """
        if self._client is None:
            redis_url = settings.get_redis_url
            
            # 检测是否使用 TLS/SSL（rediss:// 协议）
            use_ssl = redis_url.startswith("rediss://")
            
            # 构建连接参数
            connection_kwargs = {
                "encoding": "utf-8",
                "decode_responses": True,
                # 超时配置和连接池设置
                "socket_timeout": 5,  # Socket 操作超时 5 秒
                "socket_connect_timeout": 5,  # 连接超时 5 秒
                "socket_keepalive": True,  # 启用 TCP keepalive
                "max_connections": 50,  # 连接池最大连接数
                "retry_on_timeout": True,  # 超时时自动重试
            }
            
            # SSL/TLS 配置（Upstash 等云服务需要）
            # 注意：redis-py 5.x 会根据 rediss:// 协议自动启用 SSL
            # 不需要传递 ssl=True/False 参数
            if use_ssl:
                connection_kwargs["ssl_cert_reqs"] = "required"
            
            self._client = await aioredis.from_url(redis_url, **connection_kwargs)
            logger.info(
                "redis_client_initialized",
                redis_url=redis_url,
                ssl_enabled=use_ssl,
            )
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            logger.info("redis_client_closed")
    
    async def ping(self) -> bool:
        """健康检查"""
        await self.connect()
        return await self._client.ping()
    
    async def set_json(self, key: str, value: Any, ex: int | None = None):
        """存储 JSON 对象"""
        await self.connect()
        await self._client.set(key, json.dumps(value), ex=ex)
    
    async def get_json(self, key: str) -> Any | None:
        """读取 JSON 对象"""
        await self.connect()
        data = await self._client.get(key)
        return json.loads(data) if data else None
    
    async def delete(self, key: str):
        """删除键"""
        await self.connect()
        await self._client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        await self.connect()
        return await self._client.exists(key) > 0


# 全局单例
redis_client = RedisClient()


def get_redis_client() -> RedisClient:
    """
    获取 Redis 客户端实例（用于依赖注入）
    
    Returns:
        RedisClient 全局单例实例
    """
    return redis_client

