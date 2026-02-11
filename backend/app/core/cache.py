"""
Cache-Aside 模式工具函数

提供统一的缓存模式实现，支持：
- 自动序列化/反序列化（基于 Pydantic 模型）
- TTL 配置
- 缓存失效策略
- 类型安全
"""
from typing import Any, Callable, TypeVar, Type
import structlog
from pydantic import BaseModel

from app.db.redis_client import redis_client

T = TypeVar('T', bound=BaseModel)

logger = structlog.get_logger()


async def get_or_set_cache(
    key: str,
    fetch_func: Callable[[], Any],
    model_type: Type[T],
    ttl: int = 3600,
) -> T:
    """
    Cache-Aside 模式：先查缓存，未命中则查数据库并写入缓存
    
    Args:
        key: Redis 缓存键
        fetch_func: 数据获取函数（异步协程），缓存未命中时调用
        model_type: Pydantic 模型类型（用于序列化/反序列化）
        ttl: 缓存过期时间（秒），默认 1 小时
        
    Returns:
        模型实例
        
    Example:
        ```python
        from app.models.user import User
        
        async def fetch_user_from_db():
            async with get_session() as session:
                return await user_crud.get(session, user_id=123)
        
        user = await get_or_set_cache(
            key="user:123",
            fetch_func=fetch_user_from_db,
            model_type=User,
            ttl=3600,
        )
        ```
    """
    # 1. 尝试从缓存读取
    # 注意：msgspec 不支持直接解码为 Pydantic 模型，所以不传递 type_ 参数
    # 先获取 dict，然后手动转换为 Pydantic 模型
    cached_data = await redis_client.get_json(key)
    if cached_data:
        logger.debug("cache_hit", key=key)
        # 如果指定了 Pydantic 模型类型，将 dict 转换为模型实例
        if isinstance(cached_data, dict) and issubclass(model_type, BaseModel):
            return model_type.model_validate(cached_data)
        return cached_data
    
    # 2. 缓存未命中，调用获取函数
    logger.debug("cache_miss", key=key)
    data = await fetch_func()
    
    if data is None:
        # 数据不存在，不缓存 None（避免缓存穿透）
        return None
    
    # 3. 写入缓存
    try:
        # 如果 data 是 Pydantic 模型，转换为字典
        if isinstance(data, BaseModel):
            cache_value = data.model_dump()
        else:
            cache_value = data
        
        await redis_client.set_json(key, cache_value, ex=ttl)
        logger.debug("cache_set", key=key, ttl=ttl)
    except Exception as e:
        # 缓存写入失败不应影响业务逻辑
        logger.warning("cache_set_failed", key=key, error=str(e))
    
    return data


async def invalidate_cache(key: str):
    """
    使缓存失效（删除缓存键）
    
    Args:
        key: Redis 缓存键
        
    Example:
        ```python
        # 用户信息更新后，删除缓存
        await invalidate_cache("user:123")
        ```
    """
    try:
        await redis_client.delete(key)
        logger.debug("cache_invalidated", key=key)
    except Exception as e:
        logger.warning("cache_invalidation_failed", key=key, error=str(e))


async def invalidate_cache_pattern(pattern: str):
    """
    批量使缓存失效（根据模式匹配）
    
    ⚠️ 注意：SCAN 操作在大规模数据时可能较慢，生产环境慎用
    
    Args:
        pattern: Redis 键模式（支持通配符 *）
        
    Example:
        ```python
        # 删除所有用户相关缓存
        await invalidate_cache_pattern("user:*")
        ```
    """
    try:
        await redis_client.connect()
        client = redis_client._client
        
        cursor = 0
        deleted_count = 0
        
        while True:
            cursor, keys = await client.scan(cursor, match=pattern, count=100)
            if keys:
                await client.delete(*keys)
                deleted_count += len(keys)
            
            if cursor == 0:
                break
        
        logger.info("cache_pattern_invalidated", pattern=pattern, deleted_count=deleted_count)
    except Exception as e:
        logger.warning("cache_pattern_invalidation_failed", pattern=pattern, error=str(e))


async def set_cache(key: str, value: Any, ttl: int = 3600):
    """
    直接设置缓存（不使用 Cache-Aside 模式）
    
    用于显式缓存场景，例如：
    - Token 验证结果
    - 临时计算结果
    - 会话数据
    
    Args:
        key: Redis 缓存键
        value: 待缓存的值（支持 Pydantic 模型、dict、str 等）
        ttl: 缓存过期时间（秒）
        
    Example:
        ```python
        # 缓存 Token 验证结果
        await set_cache("token:abc123", {"user_id": 1, "valid": True}, ttl=86400)
        ```
    """
    try:
        if isinstance(value, BaseModel):
            value = value.model_dump()
        
        await redis_client.set_json(key, value, ex=ttl)
        logger.debug("cache_set_explicit", key=key, ttl=ttl)
    except Exception as e:
        logger.warning("cache_set_explicit_failed", key=key, error=str(e))


async def get_cache(key: str, model_type: Type[T] | None = None) -> T | Any | None:
    """
    直接读取缓存（不使用 Cache-Aside 模式）
    
    Args:
        key: Redis 缓存键
        model_type: Pydantic 模型类型（可选，用于类型安全）
        
    Returns:
        缓存值（如果存在），否则返回 None
        
    Example:
        ```python
        # 读取 Token 验证结果
        token_data = await get_cache("token:abc123")
        if token_data and token_data["valid"]:
            user_id = token_data["user_id"]
        ```
    """
    try:
        return await redis_client.get_json(key, type_=model_type)
    except Exception as e:
        logger.warning("cache_get_failed", key=key, error=str(e))
        return None

