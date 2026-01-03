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
    """
    Redis 异步客户端封装
    
    设计说明：
    - 全局单例模式：便于在任何地方访问，无需传递实例
    - 事件循环感知：检测循环切换（如 asyncio.run() 创建新循环），自动重建连接
    - 连接池复用：redis-py 内部使用连接池，提高性能
    """
    
    def __init__(self):
        self._client: aioredis.Redis | None = None
        self._loop_id: int | None = None  # 记录连接创建时的事件循环 ID
    
    async def connect(self):
        """
        建立连接
        
        支持标准 Redis 和 Upstash Redis（通过 rediss:// 协议使用 TLS/SSL）
        
        自动检测事件循环切换（如每次 asyncio.run() 创建新循环），重新建立连接。
        这是必要的，因为：
        1. redis-py 的 ConnectionPool 绑定到特定事件循环
        2. asyncio.run() 每次创建新循环
        3. 我们使用全局单例模式
        """
        import asyncio
        
        try:
            current_loop_id = id(asyncio.get_running_loop())
        except RuntimeError:
            # 如果没有运行中的循环，获取当前设置的循环
            current_loop_id = id(asyncio.get_event_loop())
        
        # 检测事件循环切换，重新建立连接
        if self._client is not None and self._loop_id != current_loop_id:
            logger.debug(
                "redis_event_loop_changed_recreating_connection",
                old_loop_id=self._loop_id,
                new_loop_id=current_loop_id,
            )
            try:
                await self._client.close()
            except Exception as e:
                logger.warning("redis_close_old_connection_failed", error=str(e))
            self._client = None
            self._loop_id = None
        
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
            self._loop_id = current_loop_id  # 记录当前事件循环 ID
            logger.info(
                "redis_client_initialized",
                redis_url=redis_url,
                ssl_enabled=use_ssl,
                loop_id=current_loop_id,
            )
    
    async def close(self):
        """关闭连接"""
        if self._client:
            await self._client.close()
            self._client = None
            self._loop_id = None
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

