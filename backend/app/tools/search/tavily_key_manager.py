"""
Tavily API Key 池化管理器

职责：
- 管理多个 API Keys 的轮换和选择
- 通过 Tavily /usage API 获取真实配额信息
- 健康检查和故障转移
- 智能选择最优 Key（基于剩余配额和成功率）

设计原则：
- 配额感知选择（Quota-aware Selection）
- 使用 Tavily 官方 API 查询配额（而非本地计数）
- 配额信息缓存（减少 API 调用）
- 优雅降级（API 不可用时降级为 Round Robin）
- 高可用性（自动故障转移）
"""
import asyncio
import time
import hashlib
import structlog
import httpx
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

from app.db.redis_client import RedisClient
from app.config.settings import settings

logger = structlog.get_logger()


# Tavily Usage API 常量
TAVILY_USAGE_API_URL = "https://api.tavily.com/usage"
USAGE_CACHE_TTL = 60  # 配额信息缓存 60 秒


@dataclass
class TavilyUsageInfo:
    """Tavily API 配额信息（从 /usage API 获取）"""
    key_usage: int  # API Key 当前使用次数
    key_limit: Optional[int]  # API Key 限制（None 表示无限制）
    plan_name: str  # 账户计划名称
    plan_usage: int  # 计划当前使用次数
    plan_limit: int  # 计划限制
    paygo_usage: int  # Pay-as-you-go 使用次数
    paygo_limit: int  # Pay-as-you-go 限制
    
    @property
    def key_remaining(self) -> int:
        """Key 剩余配额"""
        if self.key_limit is None or self.key_limit == 2147483647:
            # 无限制，返回一个大数
            return 999999
        return max(0, self.key_limit - self.key_usage)
    
    @property
    def plan_remaining(self) -> int:
        """计划剩余配额"""
        return max(0, self.plan_limit - self.plan_usage)
    
    @property
    def total_remaining(self) -> int:
        """总剩余配额（取 Key 和计划的最小值）"""
        return min(self.key_remaining, self.plan_remaining)


@dataclass
class KeyStats:
    """API Key 统计信息"""
    key_id: str  # Key 的唯一标识（前缀哈希）
    key_index: int  # Key 在列表中的索引
    total_calls: int  # 总调用次数（本地计数）
    success_calls: int  # 成功次数
    failed_calls: int  # 失败次数
    rate_limit_errors: int  # 限流错误次数
    last_used_at: Optional[datetime]  # 最后使用时间
    is_healthy: bool  # 健康状态
    usage_info: Optional[TavilyUsageInfo]  # 真实配额信息（从 Tavily API 获取）
    
    @property
    def success_rate(self) -> float:
        """成功率（0-1）"""
        if self.total_calls == 0:
            return 1.0
        return self.success_calls / self.total_calls
    
    @property
    def remaining_quota(self) -> int:
        """剩余配额（从 Tavily API 获取）"""
        if self.usage_info:
            return self.usage_info.total_remaining
        # 如果没有配额信息，返回一个默认值
        return 1000


class TavilyAPIKeyManager:
    """
    Tavily API Key 池化管理器
    
    核心功能：
    1. 配额追踪：在 Redis 中追踪每个 Key 的使用情况
    2. 智能选择：基于剩余配额、成功率、响应时间选择最优 Key
    3. 健康检查：定期检测 Key 的健康状态
    4. 故障转移：自动切换到其他可用 Key
    5. 优雅降级：Redis 不可用时降级为简单 Round Robin
    """
    
    def __init__(self, redis_client: RedisClient, api_keys: list[str]):
        """
        初始化 Key Manager
        
        Args:
            redis_client: Redis 客户端实例
            api_keys: API Key 列表
        """
        if not api_keys:
            raise ValueError("至少需要提供一个 Tavily API Key")
        
        self.redis = redis_client
        self.api_keys = api_keys
        self._current_index = 0  # Round Robin 索引（用于降级）
        self._lock = asyncio.Lock()  # 并发控制
        
        logger.info(
            "tavily_key_manager_initialized",
            total_keys=len(api_keys),
            quota_tracking_enabled=settings.TAVILY_QUOTA_TRACKING_ENABLED,
        )
    
    def _get_key_id(self, key_index: int) -> str:
        """
        获取 Key 的唯一标识（用于 Redis 键名）
        
        使用 SHA256 哈希的前 8 位，避免在日志中暴露完整 Key
        
        Args:
            key_index: Key 索引
            
        Returns:
            Key ID（8 位哈希）
        """
        api_key = self.api_keys[key_index]
        hash_obj = hashlib.sha256(api_key.encode())
        return hash_obj.hexdigest()[:8]
    
    def _get_redis_key(self, key_index: int, suffix: str) -> str:
        """
        构建 Redis 键名
        
        Args:
            key_index: Key 索引
            suffix: 键名后缀（如 "usage_cache", "stats:total_calls"）
            
        Returns:
            完整的 Redis 键名
        """
        key_id = self._get_key_id(key_index)
        return f"tavily:{key_id}:{suffix}"
    
    async def _fetch_usage_from_api(self, key_index: int) -> Optional[TavilyUsageInfo]:
        """
        从 Tavily API 获取配额信息
        
        Args:
            key_index: Key 索引
            
        Returns:
            TavilyUsageInfo 对象，失败时返回 None
        """
        api_key = self.api_keys[key_index]
        key_id = self._get_key_id(key_index)
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    TAVILY_USAGE_API_URL,
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 解析响应
                    key_data = data.get("key", {})
                    account_data = data.get("account", {})
                    
                    usage_info = TavilyUsageInfo(
                        key_usage=key_data.get("usage", 0),
                        key_limit=key_data.get("limit"),  # 可能为 None
                        plan_name=account_data.get("current_plan", "Unknown"),
                        plan_usage=account_data.get("plan_usage", 0),
                        plan_limit=account_data.get("plan_limit", 0),
                        paygo_usage=account_data.get("paygo_usage", 0),
                        paygo_limit=account_data.get("paygo_limit", 0),
                    )
                    
                    logger.info(
                        "tavily_usage_fetched",
                        key_index=key_index,
                        key_id=key_id,
                        key_usage=usage_info.key_usage,
                        key_limit=usage_info.key_limit,
                        plan_remaining=usage_info.plan_remaining,
                    )
                    
                    return usage_info
                else:
                    logger.warning(
                        "tavily_usage_api_error",
                        key_index=key_index,
                        key_id=key_id,
                        status_code=response.status_code,
                        response=response.text[:200],
                    )
                    return None
                    
        except Exception as e:
            logger.warning(
                "tavily_usage_api_failed",
                key_index=key_index,
                key_id=key_id,
                error=str(e),
            )
            return None
    
    async def _get_cached_usage(self, key_index: int) -> Optional[TavilyUsageInfo]:
        """
        获取缓存的配额信息
        
        Args:
            key_index: Key 索引
            
        Returns:
            TavilyUsageInfo 对象，缓存不存在或过期时返回 None
        """
        try:
            await self.redis.connect()
            client = self.redis._client
            
            cache_key = self._get_redis_key(key_index, "usage_cache")
            cached_data = await client.get(cache_key)
            
            if cached_data:
                import json
                data = json.loads(cached_data)
                
                usage_info = TavilyUsageInfo(
                    key_usage=data["key_usage"],
                    key_limit=data.get("key_limit"),
                    plan_name=data["plan_name"],
                    plan_usage=data["plan_usage"],
                    plan_limit=data["plan_limit"],
                    paygo_usage=data["paygo_usage"],
                    paygo_limit=data["paygo_limit"],
                )
                
                return usage_info
            
            return None
            
        except Exception as e:
            logger.warning(
                "get_cached_usage_failed",
                key_index=key_index,
                error=str(e),
            )
            return None
    
    async def _cache_usage(self, key_index: int, usage_info: TavilyUsageInfo) -> None:
        """
        缓存配额信息
        
        Args:
            key_index: Key 索引
            usage_info: 配额信息
        """
        try:
            await self.redis.connect()
            client = self.redis._client
            
            cache_key = self._get_redis_key(key_index, "usage_cache")
            
            import json
            data = {
                "key_usage": usage_info.key_usage,
                "key_limit": usage_info.key_limit,
                "plan_name": usage_info.plan_name,
                "plan_usage": usage_info.plan_usage,
                "plan_limit": usage_info.plan_limit,
                "paygo_usage": usage_info.paygo_usage,
                "paygo_limit": usage_info.paygo_limit,
            }
            
            await client.set(cache_key, json.dumps(data), ex=USAGE_CACHE_TTL)
            
        except Exception as e:
            logger.warning(
                "cache_usage_failed",
                key_index=key_index,
                error=str(e),
            )
    
    async def get_usage_info(self, key_index: int, force_refresh: bool = False) -> Optional[TavilyUsageInfo]:
        """
        获取 Key 的配额信息（优先使用缓存）
        
        Args:
            key_index: Key 索引
            force_refresh: 是否强制刷新（跳过缓存）
            
        Returns:
            TavilyUsageInfo 对象，失败时返回 None
        """
        # 如果不强制刷新，先尝试从缓存获取
        if not force_refresh:
            cached = await self._get_cached_usage(key_index)
            if cached:
                return cached
        
        # 从 API 获取
        usage_info = await self._fetch_usage_from_api(key_index)
        
        # 缓存结果
        if usage_info:
            await self._cache_usage(key_index, usage_info)
        
        return usage_info
    
    
    async def get_key_stats(self, key_index: int) -> KeyStats:
        """
        获取 Key 的统计信息（包含真实配额信息）
        
        Args:
            key_index: Key 索引
            
        Returns:
            KeyStats 对象
        """
        key_id = self._get_key_id(key_index)
        
        try:
            await self.redis.connect()
            client = self.redis._client
            
            # 读取本地统计信息
            stats_prefix = f"tavily:stats:{key_id}"
            total_calls = int(await client.get(f"{stats_prefix}:total_calls") or 0)
            success_calls = int(await client.get(f"{stats_prefix}:success_calls") or 0)
            failed_calls = int(await client.get(f"{stats_prefix}:failed_calls") or 0)
            rate_limit_errors = int(await client.get(f"{stats_prefix}:rate_limit_errors") or 0)
            
            # 读取健康状态
            health_prefix = f"tavily:health:{key_id}"
            is_healthy = await client.get(f"{health_prefix}:status") != "unhealthy"
            
            # 读取最后使用时间
            last_used_ts = await client.get(f"{stats_prefix}:last_used_at")
            last_used_at = datetime.fromtimestamp(float(last_used_ts)) if last_used_ts else None
            
            # 获取真实配额信息（从 Tavily API）
            usage_info = await self.get_usage_info(key_index)
            
            return KeyStats(
                key_id=key_id,
                key_index=key_index,
                total_calls=total_calls,
                success_calls=success_calls,
                failed_calls=failed_calls,
                rate_limit_errors=rate_limit_errors,
                last_used_at=last_used_at,
                is_healthy=is_healthy,
                usage_info=usage_info,
            )
            
        except Exception as e:
            logger.warning(
                "redis_get_key_stats_failed",
                key_index=key_index,
                error=str(e),
            )
            # 降级：返回默认统计信息
            return KeyStats(
                key_id=key_id,
                key_index=key_index,
                total_calls=0,
                success_calls=0,
                failed_calls=0,
                rate_limit_errors=0,
                last_used_at=None,
                is_healthy=True,
                usage_info=None,
            )
    
    async def _calculate_key_score(self, stats: KeyStats) -> float:
        """
        计算 Key 的优先级分数（越高越好）
        
        评分策略：
        - 剩余配额权重 70%（基于 Tavily API 真实数据）
        - 成功率权重 20%
        - 最近使用时间权重 10%（越晚使用分数越低，鼓励轮换）
        
        Args:
            stats: Key 统计信息
            
        Returns:
            优先级分数（0-100）
        """
        # 1. 剩余配额分数（70%）
        # 使用真实的配额信息
        if stats.usage_info:
            # 使用总剩余配额（Key 限制和计划限制的最小值）
            total_remaining = stats.usage_info.total_remaining
            
            # 计算配额比例（假设合理的总配额）
            # 如果 Key 无限制，使用计划限制；如果都无限制，使用固定值
            if stats.usage_info.plan_limit > 0:
                quota_ratio = min(total_remaining / stats.usage_info.plan_limit, 1.0)
            else:
                # 没有配额信息，给予中等分数
                quota_ratio = 0.5
            
            quota_score = quota_ratio * 70
        else:
            # 没有配额信息，给予中等分数
            quota_score = 35
        
        # 2. 成功率分数（20%）
        success_score = stats.success_rate * 20
        
        # 3. 最近使用时间分数（10%）
        # 如果最近使用过，降低分数（鼓励轮换）
        if stats.last_used_at:
            time_since_use = (datetime.now() - stats.last_used_at).total_seconds()
            # 60 秒内使用过，分数降低；超过 60 秒，满分
            recency_score = min(time_since_use / 60, 1.0) * 10
        else:
            recency_score = 10  # 从未使用过，满分
        
        total_score = quota_score + success_score + recency_score
        
        return total_score
    
    async def get_best_key(self) -> tuple[str, int]:
        """
        选择当前最优的 API Key
        
        策略：
        1. 过滤不健康的 Key
        2. 过滤配额已用尽的 Key
        3. 计算每个 Key 的优先级分数
        4. 返回分数最高的 Key
        5. 如果所有 Key 都不可用，使用 Round Robin 降级策略
        
        Returns:
            (api_key, key_index) 元组
            
        Raises:
            ValueError: 如果所有 Key 都不可用
        """
        async with self._lock:
            # 如果未启用配额追踪，使用简单的 Round Robin
            if not settings.TAVILY_QUOTA_TRACKING_ENABLED:
                key_index = self._current_index
                self._current_index = (self._current_index + 1) % len(self.api_keys)
                
                logger.info(
                    "tavily_key_selected_round_robin",
                    key_index=key_index,
                    key_prefix=self.api_keys[key_index][:10] + "...",
                )
                
                return self.api_keys[key_index], key_index
            
            # 配额感知选择
            try:
                candidates = []
                
                # 收集所有候选 Key 的统计信息
                for idx in range(len(self.api_keys)):
                    stats = await self.get_key_stats(idx)
                    
                    # 过滤不健康的 Key
                    if not stats.is_healthy:
                        logger.debug(
                            "tavily_key_unhealthy_skipped",
                            key_index=idx,
                            key_id=stats.key_id,
                        )
                        continue
                    
                    # 过滤配额已用尽的 Key
                    if stats.usage_info and stats.usage_info.total_remaining <= 0:
                        logger.debug(
                            "tavily_key_quota_exhausted_skipped",
                            key_index=idx,
                            key_id=stats.key_id,
                            remaining_quota=stats.usage_info.total_remaining,
                        )
                        continue
                    
                    # 计算优先级分数
                    score = await self._calculate_key_score(stats)
                    candidates.append((idx, stats, score))
                
                # 如果没有可用候选，降级为 Round Robin
                if not candidates:
                    logger.warning(
                        "tavily_all_keys_unavailable_fallback_round_robin",
                        total_keys=len(self.api_keys),
                    )
                    key_index = self._current_index
                    self._current_index = (self._current_index + 1) % len(self.api_keys)
                    return self.api_keys[key_index], key_index
                
                # 选择分数最高的 Key
                best_idx, best_stats, best_score = max(candidates, key=lambda x: x[2])
                
                logger.info(
                    "tavily_key_selected_quota_aware",
                    key_index=best_idx,
                    key_id=best_stats.key_id,
                    score=round(best_score, 2),
                    remaining_quota=best_stats.remaining_quota if best_stats.usage_info else "unknown",
                    success_rate=round(best_stats.success_rate, 2),
                )
                
                return self.api_keys[best_idx], best_idx
                
            except Exception as e:
                logger.error(
                    "tavily_key_selection_failed_fallback_round_robin",
                    error=str(e),
                )
                # 降级为 Round Robin
                key_index = self._current_index
                self._current_index = (self._current_index + 1) % len(self.api_keys)
                return self.api_keys[key_index], key_index
    
    async def mark_key_used(
        self, 
        key_index: int, 
        success: bool, 
        error_type: Optional[str] = None
    ) -> None:
        """
        记录 Key 的使用情况
        
        Args:
            key_index: Key 索引
            success: 是否成功
            error_type: 错误类型（"rate_limit", "timeout", "auth", "network", "unknown"）
        """
        key_id = self._get_key_id(key_index)
        
        try:
            await self.redis.connect()
            client = self.redis._client
            
            # 更新本地统计信息（用于成功率计算）
            stats_prefix = f"tavily:stats:{key_id}"
            await client.incr(f"{stats_prefix}:total_calls")
            
            if success:
                await client.incr(f"{stats_prefix}:success_calls")
            else:
                await client.incr(f"{stats_prefix}:failed_calls")
                
                if error_type == "rate_limit":
                    await client.incr(f"{stats_prefix}:rate_limit_errors")
            
            # 更新最后使用时间
            await client.set(f"{stats_prefix}:last_used_at", time.time())
            
            # 如果成功使用，使配额缓存失效（下次调用时会重新获取最新配额）
            if success:
                cache_key = self._get_redis_key(key_index, "usage_cache")
                await client.delete(cache_key)
            
            logger.debug(
                "tavily_key_marked_used",
                key_index=key_index,
                key_id=key_id,
                success=success,
                error_type=error_type,
            )
            
        except Exception as e:
            logger.warning(
                "redis_mark_key_used_failed",
                key_index=key_index,
                error=str(e),
            )
    
    async def check_key_health(self, key_index: int) -> bool:
        """
        检查 Key 是否健康
        
        健康判定策略：
        - 如果最近 5 分钟内有 3 次以上限流错误 → 不健康
        - 如果连续 10 次失败 → 不健康
        - 如果成功率低于 50% 且总调用次数 > 10 → 不健康
        
        Args:
            key_index: Key 索引
            
        Returns:
            True 表示健康，False 表示不健康
        """
        stats = await self.get_key_stats(key_index)
        
        # 规则 1: 最近限流错误过多
        if stats.rate_limit_errors >= 3:
            logger.warning(
                "tavily_key_unhealthy_too_many_rate_limits",
                key_index=key_index,
                key_id=stats.key_id,
                rate_limit_errors=stats.rate_limit_errors,
            )
            await self._mark_key_unhealthy(key_index)
            return False
        
        # 规则 2: 连续失败过多
        if stats.total_calls > 10 and stats.success_rate < 0.5:
            logger.warning(
                "tavily_key_unhealthy_low_success_rate",
                key_index=key_index,
                key_id=stats.key_id,
                success_rate=round(stats.success_rate, 2),
            )
            await self._mark_key_unhealthy(key_index)
            return False
        
        # 健康
        await self._mark_key_healthy(key_index)
        return True
    
    async def _mark_key_healthy(self, key_index: int) -> None:
        """标记 Key 为健康状态"""
        try:
            await self.redis.connect()
            client = self.redis._client
            key_id = self._get_key_id(key_index)
            
            health_prefix = f"tavily:health:{key_id}"
            await client.set(f"{health_prefix}:status", "healthy")
            await client.set(f"{health_prefix}:last_check", time.time())
            
        except Exception as e:
            logger.warning(
                "redis_mark_healthy_failed",
                key_index=key_index,
                error=str(e),
            )
    
    async def _mark_key_unhealthy(self, key_index: int) -> None:
        """标记 Key 为不健康状态"""
        try:
            await self.redis.connect()
            client = self.redis._client
            key_id = self._get_key_id(key_index)
            
            health_prefix = f"tavily:health:{key_id}"
            await client.set(f"{health_prefix}:status", "unhealthy")
            await client.set(f"{health_prefix}:last_check", time.time())
            # 不健康状态保持 5 分钟，之后自动恢复
            await client.expire(f"{health_prefix}:status", 300)
            
        except Exception as e:
            logger.warning(
                "redis_mark_unhealthy_failed",
                key_index=key_index,
                error=str(e),
            )
    
    async def get_all_stats(self) -> list[KeyStats]:
        """
        获取所有 Keys 的统计信息
        
        Returns:
            KeyStats 列表
        """
        stats_list = []
        for idx in range(len(self.api_keys)):
            stats = await self.get_key_stats(idx)
            stats_list.append(stats)
        return stats_list

