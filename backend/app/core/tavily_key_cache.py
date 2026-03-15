"""
Tavily API Key Redis 缓存管理器

职责：
- 应用启动时从数据库加载所有可用 Key 到 Redis
- 提供快速的 Key 获取接口（无需查询数据库）
- 支持随机选择或负载均衡策略
- 定期刷新缓存（通过后台任务）

优势：
- 消除运行时数据库依赖
- 提高性能（Redis vs PostgreSQL）
- 避免连接池耗尽
- 更符合微服务架构
"""
import random
import structlog
from typing import Optional
from datetime import datetime

from app.db.redis_client import redis_client

logger = structlog.get_logger()


class TavilyKeyCacheManager:
    """
    Tavily API Key Redis 缓存管理器
    
    架构设计：
    1. 应用启动时调用 initialize() 加载所有 Key
    2. 运行时调用 get_random_key() 获取可用 Key（无需数据库）
    3. 后台任务定期调用 refresh() 更新缓存
    
    Redis 数据结构：
    - tavily:keys:available - Set[key_id] - 所有可用的 Key ID
    - tavily:key:{key_id} - Hash - Key 详细信息
      {
        "api_key": "tvly-xxx",
        "plan_limit": 1000,
        "remaining_quota": 750,
        "last_updated": "2026-01-13T01:30:00",
        "is_active": "true"
      }
    """
    
    # Redis Key 前缀
    KEYS_SET = "tavily:keys:available"
    KEY_DETAIL_PREFIX = "tavily:key:"
    CACHE_VERSION = "tavily:cache:version"  # 用于追踪缓存版本
    
    def __init__(self):
        """初始化管理器"""
        self.redis = redis_client
        self._raw_client = None  # 延迟初始化，在 connect 时设置
    
    async def initialize(self) -> int:
        """
        从数据库加载所有可用 Key 到 Redis
        
        应用启动时调用，确保 Redis 缓存是最新的
        
        Returns:
            加载的 Key 数量
            
        Raises:
            Exception: 数据库查询失败
        """
        from app.db.session import async_session_maker
        from app.models.database import TavilyAPIKey
        from sqlalchemy import select
        
        logger.info("tavily_key_cache_initializing")
        
        try:
            async with async_session_maker() as session:
                # 查询所有有配额的 Key
                stmt = select(TavilyAPIKey).where(
                    TavilyAPIKey.remaining_quota > 0,
                )
                result = await session.execute(stmt)
                keys = result.scalars().all()
                
                if not keys:
                    logger.warning("tavily_key_cache_no_keys_found")
                    return 0
                
                # 确保 Redis 连接
                await self.redis.connect()
                
                # 清空旧缓存
                await self.redis._client.delete(self.KEYS_SET)
                
                # 写入新缓存
                loaded_count = 0
                for key_record in keys:
                    success = await self._cache_key(key_record)
                    if success:
                        loaded_count += 1
                
                # 更新缓存版本
                await self.redis._client.set(
                    self.CACHE_VERSION,
                    datetime.utcnow().isoformat()
                )
                
                logger.info(
                    "tavily_key_cache_initialized",
                    total_keys=len(keys),
                    loaded_keys=loaded_count,
                )
                
                return loaded_count
                
        except Exception as e:
            logger.error(
                "tavily_key_cache_init_failed",
                error=str(e),
                exc_info=True,
            )
            raise
    
    async def refresh(self) -> int:
        """
        刷新 Redis 缓存
        
        定时任务调用，更新 Key 的配额信息
        
        Returns:
            刷新的 Key 数量
        """
        logger.info("tavily_key_cache_refreshing")
        return await self.initialize()  # 完全重新加载
    
    async def _cache_key(self, key_record) -> bool:
        """
        将单个 Key 写入 Redis
        
        Args:
            key_record: TavilyAPIKey 数据库记录
            
        Returns:
            是否成功
        """
        try:
            # ✅ 使用 api_key 作为 key_id（因为 TavilyAPIKey 没有独立的 id 字段）
            key_id = key_record.api_key
            key_hash = f"{self.KEY_DETAIL_PREFIX}{key_id}"
            
            # 存储 Key 详细信息
            key_data = {
                "api_key": key_record.api_key,
                "plan_limit": str(key_record.plan_limit),
                "remaining_quota": str(key_record.remaining_quota),
                "last_updated": datetime.utcnow().isoformat(),
            }
            
            # 说明：
            # 这里不再给详情 hash 设置 TTL。
            # 如果只有详情 hash 过期，而可用 key 的 Set 永不过期，
            # Redis 中就会残留“Set 里有 key_id、详情 hash 已消失”的孤儿项。
            # 在不依赖单独 beat 的运行模式下，这类孤儿项会持续累积并导致误判。
            await self.redis._client.hset(key_hash, mapping=key_data)
            
            # 添加到可用 Key 集合
            await self.redis._client.sadd(self.KEYS_SET, key_id)
            
            logger.debug(
                "tavily_key_cached",
                key_id=key_id,
                key_prefix=key_record.api_key[:10] + "...",
                remaining_quota=key_record.remaining_quota,
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "tavily_key_cache_failed",
                key_id=getattr(key_record, 'api_key', 'unknown')[:10] + "...",
                error=str(e),
            )
            return False
    
    async def _cleanup_invalid_key_ids(self, key_ids: list[str]) -> None:
        """
        批量清理失效的 key_id

        Args:
            key_ids: 需要清理的 key_id 列表
        """
        unique_key_ids = list(dict.fromkeys(key_ids))
        for key_id in unique_key_ids:
            await self.redis._client.srem(self.KEYS_SET, key_id)

        logger.debug(
            "tavily_keys_auto_cleaned",
            cleaned_count=len(unique_key_ids),
        )


    async def _refresh_cache_on_demand(self, reason: str) -> int:
        """
        按需刷新缓存

        Args:
            reason: 触发刷新原因

        Returns:
            刷新的 Key 数量
        """
        logger.warning(
            "tavily_key_cache_on_demand_refresh_started",
            reason=reason,
            message="当前未依赖定时任务，检测到脏缓存后主动回源刷新",
        )
        refreshed_count = await self.refresh()
        logger.info(
            "tavily_key_cache_on_demand_refresh_completed",
            reason=reason,
            refreshed_count=refreshed_count,
        )
        return refreshed_count


    async def _select_random_key_once(self, min_quota: int = 1, max_retries: int = 5) -> Optional[str]:
        """
        单次从当前缓存中选择可用 Key

        Args:
            min_quota: 最小所需配额
            max_retries: 最大重试次数（仅用于日志兼容）

        Returns:
            可用 API Key，如果当前缓存中没有则返回 None
        """
        key_ids = await self.redis._client.smembers(self.KEYS_SET)

        if not key_ids:
            logger.warning("tavily_key_cache_empty")
            return None

        # 转换为列表并打乱顺序（避免总是选中同一个 Key）
        key_ids_list = list(key_ids)
        random.shuffle(key_ids_list)

        # 说明：
        # Redis Set 中可能同时存在「已失效的 key」和「仍然有效的 key」。
        # 如果只检查前几个随机 key，就可能在缓存里明明还有可用 key 的情况下误判为全部不可用。
        # 因此这里固定遍历当前缓存集合一次，确保不会遗漏后面的有效 key。
        attempts = 0
        cleaned_keys = []

        if max_retries < len(key_ids_list):
            logger.info(
                "tavily_key_retry_limit_expanded",
                configured_max_retries=max_retries,
                effective_attempts=len(key_ids_list),
                total_keys=len(key_ids_list),
                message="为避免遗漏有效 Key，当前会遍历缓存中的全部 Key 一次",
            )

        for key_id in key_ids_list:
            attempts += 1
            key_hash = f"{self.KEY_DETAIL_PREFIX}{key_id}"

            # 获取 Key 详情
            key_data = await self.redis._client.hgetall(key_hash)

            if not key_data:
                logger.debug(
                    "tavily_key_not_found_in_cache",
                    key_id=key_id[:10] + "...",
                )
                cleaned_keys.append(key_id)
                continue

            # 检查配额（decode_responses=True，返回的是 str）
            remaining_quota = int(key_data.get("remaining_quota", 0))
            if remaining_quota < min_quota:
                logger.debug(
                    "tavily_key_quota_insufficient",
                    key_id=key_id[:10] + "...",
                    remaining_quota=remaining_quota,
                    min_quota=min_quota,
                )
                if remaining_quota <= 0:
                    cleaned_keys.append(key_id)
                continue

            # ✅ 找到可用的 Key
            api_key = key_data.get("api_key")

            logger.info(
                "tavily_key_selected_from_cache",
                key_id=key_id[:10] + "...",
                key_prefix=api_key[:10] + "..." if api_key else "unknown",
                remaining_quota=remaining_quota,
                attempts=attempts,
            )

            # 清理失效的 Key（批量）
            if cleaned_keys:
                await self._cleanup_invalid_key_ids(cleaned_keys)

            return api_key

        # 所有 Key 都不可用
        logger.warning(
            "tavily_no_available_keys_in_cache",
            total_keys=len(key_ids_list),
            attempts=attempts,
            cleaned_keys=len(cleaned_keys),
        )

        if cleaned_keys:
            await self._cleanup_invalid_key_ids(cleaned_keys)

        return None


    async def get_random_key(self, min_quota: int = 1, max_retries: int = 5) -> Optional[str]:
        """
        从 Redis 随机获取一个可用的 API Key（带重试机制）
        
        策略：
        1. 从可用 Key 集合中随机选择
        2. 检查配额是否充足（>= min_quota）
        3. 如果选中的 Key 配额不足，自动重试其他 Key
        4. 最多重试 max_retries 次
        
        Args:
            min_quota: 最小所需配额（默认 1）
            max_retries: 最大重试次数（默认 5）
        
        Returns:
            API Key 字符串，如果没有可用 Key 则返回 None
            
        Note:
            这个方法不需要数据库连接，性能极高
        """
        try:
            # 确保 Redis 连接
            await self.redis.connect()
            
            api_key = await self._select_random_key_once(
                min_quota=min_quota,
                max_retries=max_retries,
            )
            if api_key:
                return api_key

            # 不依赖单独 beat 时，这里作为最后一道兜底：
            # 一旦发现缓存为空或全是脏数据，主动从数据库回源重建一次缓存。
            refreshed_count = await self._refresh_cache_on_demand(
                reason="no_usable_key_found_in_runtime_cache",
            )
            if refreshed_count <= 0:
                return None

            return await self._select_random_key_once(
                min_quota=min_quota,
                max_retries=max_retries,
            )
            
        except Exception as e:
            logger.error(
                "tavily_key_cache_get_failed",
                error=str(e),
                exc_info=True,
            )
            return None
    
    async def get_best_key(self) -> Optional[dict]:
        """
        获取配额最多的 Key（用于需要大量调用的场景）
        
        Returns:
            Key 信息字典，包含 api_key 和 remaining_quota
        """
        try:
            await self.redis.connect()
            key_ids = await self.redis._client.smembers(self.KEYS_SET)
            
            if not key_ids:
                return None
            
            best_key = None
            max_quota = -1
            
            for key_id in key_ids:
                key_hash = f"{self.KEY_DETAIL_PREFIX}{key_id}"
                key_data = await self.redis._client.hgetall(key_hash)
                
                if not key_data:
                    continue
                
                remaining = int(key_data.get("remaining_quota", 0))
                if remaining > max_quota:
                    max_quota = remaining
                    api_key = key_data.get("api_key")
                    best_key = {
                        "api_key": api_key,
                        "remaining_quota": remaining,
                        "key_id": key_id,
                    }
            
            if best_key:
                logger.info(
                    "tavily_best_key_selected_from_cache",
                    key_prefix=best_key["api_key"][:10] + "...",
                    remaining_quota=best_key["remaining_quota"],
                )
            
            return best_key
            
        except Exception as e:
            logger.error(
                "tavily_key_cache_get_best_failed",
                error=str(e),
            )
            return None
    
    async def update_quota(self, api_key: str, used_count: int = 1) -> bool:
        """
        更新 Key 的配额（扣减使用量）
        
        Args:
            api_key: API Key 字符串
            used_count: 使用的次数（默认 1）
            
        Returns:
            是否成功更新
            
        Note:
            这是一个可选的优化，可以在运行时动态更新配额
            但不是必需的，因为定时任务会定期从数据库刷新
        """
        try:
            await self.redis.connect()
            key_hash = f"{self.KEY_DETAIL_PREFIX}{api_key}"

            if not await self.redis._client.exists(key_hash):
                logger.warning(
                    "tavily_key_not_found_for_quota_update",
                    key_prefix=api_key[:10] + "...",
                )
                return False

            # 找到了，扣减配额
            remaining_quota = await self.redis._client.hincrby(
                key_hash,
                "remaining_quota",
                -used_count
            )

            logger.debug(
                "tavily_key_quota_updated",
                key_id=api_key,
                used_count=used_count,
                remaining_quota=remaining_quota,
            )

            if remaining_quota <= 0:
                await self.redis._client.srem(self.KEYS_SET, api_key)
                logger.info(
                    "tavily_key_removed_after_quota_exhausted",
                    key_prefix=api_key[:10] + "...",
                    remaining_quota=remaining_quota,
                )

            return True
            
        except Exception as e:
            logger.error(
                "tavily_key_quota_update_failed",
                error=str(e),
            )
            return False

    async def evict_key(self, api_key: str, reason: str) -> bool:
        """
        从缓存中移除指定 Key

        Args:
            api_key: 需要移除的 API Key
            reason: 移除原因

        Returns:
            是否成功执行移除操作
        """
        try:
            await self.redis.connect()
            key_hash = f"{self.KEY_DETAIL_PREFIX}{api_key}"

            deleted_hash = await self.redis._client.delete(key_hash)
            removed_from_set = await self.redis._client.srem(self.KEYS_SET, api_key)

            logger.warning(
                "tavily_key_evicted_from_cache",
                key_prefix=api_key[:10] + "...",
                reason=reason,
                deleted_hash=deleted_hash > 0,
                removed_from_set=removed_from_set > 0,
            )
            return True

        except Exception as e:
            logger.error(
                "tavily_key_evict_failed",
                key_prefix=api_key[:10] + "...",
                reason=reason,
                error=str(e),
            )
            return False
    
    async def get_cache_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        try:
            await self.redis.connect()
            key_count = await self.redis._client.scard(self.KEYS_SET)
            cache_version = await self.redis._client.get(self.CACHE_VERSION)
            
            return {
                "total_keys": key_count,
                "cache_version": cache_version,
                "last_updated": cache_version,
            }
            
        except Exception as e:
            logger.error(
                "tavily_key_cache_stats_failed",
                error=str(e),
            )
            return {
                "total_keys": 0,
                "cache_version": None,
                "error": str(e),
            }


# 全局单例
_tavily_key_cache = None


def get_tavily_key_cache() -> TavilyKeyCacheManager:
    """
    获取 Tavily Key Cache 管理器单例
    
    Returns:
        TavilyKeyCacheManager 实例
    """
    global _tavily_key_cache
    if _tavily_key_cache is None:
        _tavily_key_cache = TavilyKeyCacheManager()
    return _tavily_key_cache

