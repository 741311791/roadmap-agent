"""
Tavily API Search Tool（基于官方 Python SDK）

职责：
- 使用官方 TavilyClient（同步客户端，按照官方示例）
- 支持完整的 API 参数（search_depth, time_range, include_domains 等）
- 多 API Key 池化管理（支持配额追踪和智能选择）
- 速率控制
- 智能重试（遇到限流自动切换 Key）
- 结果格式化

不负责：
- 回退逻辑（由 Router 处理）

官方文档：https://github.com/tavily-ai/tavily-python
"""
import asyncio
import time
import structlog
from typing import Dict, List, Optional
from collections import deque

from tavily import TavilyClient
from app.tools.base import BaseTool
from app.models.domain import SearchQuery, SearchResult
from app.config.settings import settings
from app.db.redis_client import get_redis_client
from app.tools.search.tavily_key_manager import TavilyAPIKeyManager

logger = structlog.get_logger()


class TavilyAPISearchTool(BaseTool[SearchQuery, SearchResult]):
    """
    Tavily API 搜索工具（官方 SDK + 多 Key 池化）
    
    特性：
    - 使用官方 TavilyClient（按照官方示例调用）
    - 🆕 多 API Key 池化管理（配额追踪、智能选择）
    - 🆕 智能重试（遇到限流自动切换 Key）
    - 内置速率控制（最多3个并发，最少500ms间隔）
    - 支持高级搜索参数（search_depth, time_range, include_domains 等）
    """
    
    def __init__(self):
        super().__init__(tool_id="tavily_api_search")
        
        # 🆕 使用 Key Manager 管理多个 API Keys
        api_keys = settings.get_tavily_api_keys
        if not api_keys:
            raise ValueError("未配置任何 Tavily API Key，请设置 TAVILY_API_KEY 或 TAVILY_API_KEY_LIST")
        
        # 初始化 Key Manager
        self.key_manager = TavilyAPIKeyManager(
            redis_client=get_redis_client(),
            api_keys=api_keys
        )
        
        # 🆕 为每个 Key 创建独立的 TavilyClient（延迟初始化）
        self._clients: Dict[int, TavilyClient] = {}
        
        # 速率控制 - 多层次限制
        self._search_semaphore = asyncio.Semaphore(3)  # 最多3个并发请求
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 最小请求间隔500ms
        
        # 滑动窗口速率限制器（每分钟最多100次）
        # 注意：多 Key 场景下，每个 Key 都有独立的配额，所以这里的限制可以放宽
        self._request_timestamps = deque()
        self._max_requests_per_minute = 100 * len(api_keys)  # 🆕 按 Key 数量放大
        self._rate_limit_window = 60.0
    
    def _get_client(self, key_index: int) -> TavilyClient:
        """
        获取或创建指定 Key 的 TavilyClient 实例
        
        Args:
            key_index: API Key 索引
            
        Returns:
            TavilyClient 实例
        """
        if key_index not in self._clients:
            api_key = self.key_manager.api_keys[key_index]
            self._clients[key_index] = TavilyClient(api_key=api_key)
            logger.debug(
                "tavily_client_created",
                key_index=key_index,
                key_prefix=api_key[:10] + "..."
            )
        return self._clients[key_index]
    
    async def _rate_limited_request(self, func, *args, **kwargs):
        """
        带速率限制的请求包装器
        
        功能：
        - 限制并发数量（最多3个）
        - 确保请求间隔（最少500ms）
        - 滑动窗口速率限制（每分钟最多100次）
        - 避免触发API限流
        - 使用 asyncio.to_thread 包装同步调用
        """
        async with self._search_semaphore:
            now = time.time()
            
            # 第一层：确保最小请求间隔（500ms）
            elapsed = now - self._last_request_time
            if elapsed < self._min_request_interval:
                wait_time = self._min_request_interval - elapsed
                logger.debug(
                    "tavily_api_rate_limit_min_interval",
                    wait_time=wait_time,
                    elapsed=elapsed
                )
                await asyncio.sleep(wait_time)
                now = time.time()
            
            # 第二层：滑动窗口速率限制（每分钟最多100次）
            # 清理过期的时间戳（超过60秒的）
            cutoff_time = now - self._rate_limit_window
            while self._request_timestamps and self._request_timestamps[0] < cutoff_time:
                self._request_timestamps.popleft()
            
            # 检查是否超过速率限制
            if len(self._request_timestamps) >= self._max_requests_per_minute:
                # 计算需要等待的时间（直到最旧的请求过期）
                oldest_timestamp = self._request_timestamps[0]
                wait_time = oldest_timestamp + self._rate_limit_window - now
                
                if wait_time > 0:
                    logger.warning(
                        "tavily_api_rate_limit_per_minute_throttle",
                        wait_time=wait_time,
                        requests_in_window=len(self._request_timestamps),
                        max_requests=self._max_requests_per_minute,
                        message=f"达到每分钟{self._max_requests_per_minute}次限制，等待 {wait_time:.2f}秒"
                    )
                    await asyncio.sleep(wait_time)
                    now = time.time()
                    
                    # 再次清理过期的时间戳
                    cutoff_time = now - self._rate_limit_window
                    while self._request_timestamps and self._request_timestamps[0] < cutoff_time:
                        self._request_timestamps.popleft()
            
            # 使用 asyncio.to_thread 在线程中执行同步调用
            result = await asyncio.to_thread(func, *args, **kwargs)
            
            # 记录请求时间
            self._last_request_time = time.time()
            self._request_timestamps.append(self._last_request_time)
            
            logger.debug(
                "tavily_api_request_executed",
                requests_in_last_minute=len(self._request_timestamps),
                max_requests=self._max_requests_per_minute
            )
            
            return result
    
    def _classify_error(self, error: Exception) -> str:
        """
        分类错误类型
        
        Args:
            error: 异常对象
            
        Returns:
            错误类型：
            - "rate_limit": 限流错误（429 或包含 "rate limit"）
            - "timeout": 超时错误
            - "auth": 认证错误（401 或 "unauthorized"）
            - "network": 网络错误
            - "unknown": 未知错误
        """
        error_str = str(error).lower()
        
        if "rate limit" in error_str or "429" in error_str or "too many requests" in error_str:
            return "rate_limit"
        elif "timeout" in error_str or "timed out" in error_str:
            return "timeout"
        elif "unauthorized" in error_str or "401" in error_str or "invalid api key" in error_str:
            return "auth"
        elif "network" in error_str or "connection" in error_str:
            return "network"
        else:
            return "unknown"
    
    async def execute(self, input_data: SearchQuery) -> SearchResult:
        """
        执行 Tavily API 搜索（支持智能重试）
        
        Args:
            input_data: 搜索查询，支持以下字段：
                - query: 搜索查询字符串
                - max_results: 最大结果数（默认5）
                - search_depth: 搜索深度（basic/advanced，默认advanced）
                - time_range: 时间筛选（day/week/month/year，可选）
                - include_domains: 包含的域名列表（可选）
                - exclude_domains: 排除的域名列表（可选）
            
        Returns:
            搜索结果
            
        Raises:
            ValueError: 如果所有 API Keys 都不可用
            Exception: 如果 API 调用失败
        """
        # 获取高级参数（使用默认值）
        search_depth = getattr(input_data, 'search_depth', 'advanced') or 'advanced'
        time_range = getattr(input_data, 'time_range', None)
        include_domains = getattr(input_data, 'include_domains', None)
        exclude_domains = getattr(input_data, 'exclude_domains', None)
        max_results = input_data.max_results
        
        logger.info(
            "tavily_api_search_start",
            query=input_data.query,
            max_results=max_results,
            search_depth=search_depth,
            time_range=time_range,
            total_keys=len(self.key_manager.api_keys),
        )
        
        # 🆕 智能重试：最多尝试 min(3, Key总数) 次
        max_retries = min(3, len(self.key_manager.api_keys))
        last_error = None
        
        for attempt in range(max_retries):
            # 🆕 获取最优 Key
            try:
                api_key, key_index = await self.key_manager.get_best_key()
            except Exception as e:
                logger.error(
                    "tavily_get_best_key_failed",
                    attempt=attempt + 1,
                    error=str(e),
                )
                raise ValueError(f"无法获取可用的 Tavily API Key: {e}")
            
            logger.info(
                "tavily_search_attempt",
                attempt=attempt + 1,
                max_retries=max_retries,
                key_index=key_index,
                key_prefix=api_key[:10] + "...",
            )
            
            try:
                # 执行搜索
                def do_search():
                    """执行搜索（同步调用，按照官方示例）"""
                    client = self._get_client(key_index)
                    
                    # 构建搜索参数（按照官方示例）
                    search_kwargs = {
                        "query": input_data.query,
                        "search_depth": search_depth,
                        "max_results": max_results,
                    }
                    
                    # 添加可选的高级参数
                    if time_range:
                        search_kwargs["time_range"] = time_range
                    if include_domains:
                        search_kwargs["include_domains"] = include_domains
                    if exclude_domains:
                        search_kwargs["exclude_domains"] = exclude_domains
                    
                    # 调用官方 SDK（按照官方示例）
                    response = client.search(**search_kwargs)
                    return response
                
                # 执行搜索（带速率限制）
                data = await self._rate_limited_request(do_search)
                
                # 🆕 标记 Key 使用成功
                await self.key_manager.mark_key_used(
                    key_index=key_index,
                    success=True,
                    error_type=None
                )
                
                # Tavily SDK 返回格式：{"results": [{"title", "url", "content", "score", "published_date"}], ...}
                tavily_results = data.get("results", [])
                
                results = [
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", "")[:200],  # 截取前200字符作为摘要
                        "published_date": item.get("published_date", ""),
                    }
                    for item in tavily_results[:max_results]
                ]
                
                logger.info(
                    "tavily_api_search_success",
                    query=input_data.query,
                    results_count=len(results),
                    key_index=key_index,
                    attempt=attempt + 1,
                )
                
                return SearchResult(
                    results=results,
                    total_found=len(results),
                )
                
            except Exception as e:
                # 🆕 分类错误并标记 Key 使用失败
                error_type = self._classify_error(e)
                await self.key_manager.mark_key_used(
                    key_index=key_index,
                    success=False,
                    error_type=error_type
                )
                
                logger.warning(
                    "tavily_api_search_attempt_failed",
                    query=input_data.query,
                    key_index=key_index,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error_type=error_type,
                    error=str(e)[:200],
                )
                
                last_error = e
                
                # 🆕 判断是否应该重试
                # 只有限流错误且还有重试机会时，才切换 Key 重试
                if error_type == "rate_limit" and attempt < max_retries - 1:
                    logger.info(
                        "tavily_rate_limit_retry",
                        key_index=key_index,
                        attempt=attempt + 1,
                        message="遇到限流，切换到下一个 Key 重试"
                    )
                    # 短暂延迟后重试
                    await asyncio.sleep(0.5)
                    continue
                else:
                    # 非限流错误或最后一次尝试，直接抛出
                    logger.error(
                        "tavily_api_search_failed",
                        query=input_data.query,
                        error_type=error_type,
                        error=str(e),
                    )
                    raise
        
        # 所有 Key 都失败
        error_msg = f"所有 Tavily API Keys 都不可用（尝试了 {max_retries} 次）: {last_error}"
        logger.error(
            "tavily_all_keys_failed",
            query=input_data.query,
            max_retries=max_retries,
            last_error=str(last_error),
        )
        raise ValueError(error_msg)
