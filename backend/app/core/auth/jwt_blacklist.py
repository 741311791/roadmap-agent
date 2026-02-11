"""
JWT 黑名单机制（基于 Redis）

解决问题：
- JWT 签发后无法撤销
- 用户登出后 Token 仍有效（最长 24 小时）
- 账号被盗后无法立即封禁

实现原理：
1. 使用 Redis 存储被撤销的 Token ID（jti）
2. 设置过期时间 = Token 剩余有效期
3. Token 过期后自动清理，无需手动删除
4. 鉴权时检查 Token 是否在黑名单中

性能优化：
- 使用 Redis Pipeline 批量查询
- 使用 jti（JWT ID）作为键，而非完整 Token
- 自动过期清理，避免 Redis 内存膨胀
"""
from app.db.redis_client import redis_client
import structlog

logger = structlog.get_logger()

# Redis 键前缀
JWT_BLACKLIST_PREFIX = "jwt:blacklist:"


async def add_to_blacklist(jti: str, expires_in: int):
    """
    将 Token 加入黑名单
    
    Args:
        jti: JWT ID（唯一标识符，来自 Token payload 的 "jti" 字段）
        expires_in: Token 剩余有效期（秒）
    
    原理：
    1. 使用 Redis SETEX 命令，设置带过期时间的键
    2. 键：jwt:blacklist:{jti}
    3. 值：固定为 "1"（仅作为标记，不存储额外数据）
    4. 过期时间 = Token 剩余有效期
    5. Token 过期后，Redis 自动删除键
    """
    await redis_client.connect()
    key = f"{JWT_BLACKLIST_PREFIX}{jti}"
    
    # 使用 setex 设置带过期时间的键
    await redis_client._client.setex(key, expires_in, "1")
    
    logger.info(
        "jwt_blacklisted",
        jti=jti,
        expires_in=expires_in,
        message=f"Token 已加入黑名单，{expires_in} 秒后自动清理",
    )


async def is_blacklisted(jti: str) -> bool:
    """
    检查 Token 是否在黑名单中
    
    Args:
        jti: JWT ID
        
    Returns:
        True: 已撤销（在黑名单中）
        False: 有效（不在黑名单中）
    """
    if not jti:
        return False
    
    await redis_client.connect()
    key = f"{JWT_BLACKLIST_PREFIX}{jti}"
    exists = await redis_client._client.exists(key)
    
    is_blocked = exists > 0
    
    if is_blocked:
        logger.debug("jwt_blacklist_check_blocked", jti=jti)
    
    return is_blocked


async def is_blacklisted_batch(jtis: list[str]) -> dict[str, bool]:
    """
    批量检查 Token 是否在黑名单中（性能优化）
    
    Args:
        jtis: JWT ID 列表
    
    Returns:
        字典：{jti: is_blocked}
    """
    if not jtis:
        return {}
    
    await redis_client.connect()
    
    # 使用 Redis Pipeline 批量查询（减少网络往返）
    pipe = redis_client._client.pipeline()
    
    for jti in jtis:
        key = f"{JWT_BLACKLIST_PREFIX}{jti}"
        pipe.exists(key)
    
    results = await pipe.execute()
    
    # 构建结果字典
    result_dict = {jti: bool(result) for jti, result in zip(jtis, results)}
    
    blocked_count = sum(result_dict.values())
    if blocked_count > 0:
        logger.debug(
            "jwt_blacklist_batch_check",
            total=len(jtis),
            blocked=blocked_count,
        )
    
    return result_dict


async def remove_from_blacklist(jti: str):
    """
    从黑名单中移除 Token（手动解封）
    
    注意：一般不需要手动调用，Token 过期后会自动清理
    
    Args:
        jti: JWT ID
    """
    await redis_client.connect()
    key = f"{JWT_BLACKLIST_PREFIX}{jti}"
    
    deleted = await redis_client._client.delete(key)
    
    if deleted:
        logger.info("jwt_removed_from_blacklist", jti=jti)
    else:
        logger.debug("jwt_not_in_blacklist", jti=jti)


async def clear_user_tokens(user_id: str) -> int:
    """
    清除用户所有 Token（强制登出）
    
    ⚠️ 注意：此功能需要在 JWT payload 中包含 user_id 字段，
    并且在生成 jti 时使用特定格式（如：{user_id}:{random}）
    
    Args:
        user_id: 用户 ID
        
    Returns:
        清除的token数量
    """
    await redis_client.connect()
    pattern = f"{JWT_BLACKLIST_PREFIX}*:{user_id}:*"
    
    # 扫描匹配的键（使用 SCAN 而非 KEYS，避免阻塞 Redis）
    cursor = 0
    deleted_count = 0
    
    while True:
        cursor, keys = await redis_client._client.scan(
            cursor, match=pattern, count=100
        )
        if keys:
            await redis_client._client.delete(*keys)
            deleted_count += len(keys)
        if cursor == 0:
            break
    
    logger.info(
        "user_tokens_cleared",
        user_id=user_id,
        deleted_count=deleted_count,
        message=f"已清除用户 {user_id} 的所有 Token",
    )
    
    return deleted_count


async def get_blacklist_stats() -> dict:
    """
    获取黑名单统计信息（用于监控）
    
    Returns:
        dict: 统计信息
            - total_tokens: 黑名单中的 Token 总数
            - active_tokens: 活跃的token数量（TTL > 0）
            - expired_tokens: 已过期的token数量（TTL <= 0，待清理）
    """
    await redis_client.connect()
    pattern = f"{JWT_BLACKLIST_PREFIX}*"
    
    # 扫描所有黑名单键
    cursor = 0
    all_keys = []
    
    while True:
        cursor, keys = await redis_client._client.scan(
            cursor, match=pattern, count=100
        )
        all_keys.extend(keys)
        if cursor == 0:
            break
    
    total_tokens = len(all_keys)
    
    # 获取所有键的 TTL，统计活跃和过期的token
    active_tokens = 0
    expired_tokens = 0
    
    if all_keys:
        pipe = redis_client._client.pipeline()
        for key in all_keys:
            pipe.ttl(key)
        ttls = await pipe.execute()
        
        for ttl in ttls:
            if ttl > 0:
                active_tokens += 1
            else:
                expired_tokens += 1
    
    return {
        "total_tokens": total_tokens,
        "active_tokens": active_tokens,
        "expired_tokens": expired_tokens,
    }

