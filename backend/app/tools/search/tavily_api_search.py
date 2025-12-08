"""
Tavily API Search Tool（基于官方 Python SDK）

职责：
- 使用官方 TavilyClient（同步客户端，按照官方示例）
- 支持完整的 API 参数（search_depth, time_range, include_domains 等）
- 速率控制
- 结果格式化

不负责：
- 回退逻辑（由 Router 处理）

官方文档：https://github.com/tavily-ai/tavily-python
"""
import asyncio
import time
import structlog
from typing import Dict, List, Optional

from tavily import TavilyClient
from app.tools.base import BaseTool
from app.models.domain import SearchQuery, SearchResult
from app.config.settings import settings

logger = structlog.get_logger()


class TavilyAPISearchTool(BaseTool[SearchQuery, SearchResult]):
    """
    Tavily API 搜索工具（官方 SDK）
    
    特性：
    - 使用官方 TavilyClient（按照官方示例调用）
    - 内置速率控制（最多3个并发，最少500ms间隔）
    - 支持高级搜索参数（search_depth, time_range, include_domains 等）
    """
    
    def __init__(self):
        super().__init__(tool_id="tavily_api_search")
        self.api_key = settings.TAVILY_API_KEY
        self.client = None  # 延迟初始化
        
        # 速率控制
        self._search_semaphore = asyncio.Semaphore(3)  # 最多3个并发请求
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 最小请求间隔500ms
    
    def _get_client(self) -> TavilyClient:
        """
        获取或创建 TavilyClient 实例
        
        Returns:
            TavilyClient 实例
        """
        if self.client is None:
            self.client = TavilyClient(api_key=self.api_key)
        return self.client
    
    async def _rate_limited_request(self, func, *args, **kwargs):
        """
        带速率限制的请求包装器
        
        功能：
        - 限制并发数量（最多3个）
        - 确保请求间隔（最少500ms）
        - 避免触发API限流
        - 使用 asyncio.to_thread 包装同步调用
        """
        async with self._search_semaphore:
            # 确保请求间隔
            now = time.time()
            elapsed = now - self._last_request_time
            if elapsed < self._min_request_interval:
                wait_time = self._min_request_interval - elapsed
                logger.debug(
                    "tavily_api_rate_limit_throttle",
                    wait_time=wait_time,
                    elapsed=elapsed
                )
                await asyncio.sleep(wait_time)
            
            # 使用 asyncio.to_thread 在线程中执行同步调用
            result = await asyncio.to_thread(func, *args, **kwargs)
            self._last_request_time = time.time()
            return result
    
    async def execute(self, input_data: SearchQuery) -> SearchResult:
        """
        执行 Tavily API 搜索（支持高级参数）
        
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
            ValueError: 如果 API Key 未配置
            Exception: 如果 API 调用失败
        """
        if not self.api_key or self.api_key == "your_tavily_api_key_here":
            raise ValueError("Tavily API Key 未配置，请在环境变量中设置 TAVILY_API_KEY")
        
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
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            language=input_data.language,
            content_type=input_data.content_type,
        )
        
        def do_search():
            """执行搜索（同步调用，按照官方示例）"""
            client = self._get_client()
            
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
        try:
            data = await self._rate_limited_request(do_search)
        except Exception as e:
            logger.error(
                "tavily_api_search_failed",
                error=str(e),
                query=input_data.query,
            )
            raise
        
        # Tavily SDK 返回格式：{"results": [{"title", "url", "content", "score", "published_date"}], ...}
        tavily_results = data.get("results", [])
        
        results = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", "")[:200],  # 截取前200字符作为摘要
                "published_date": item.get("published_date", ""),
                # 注意：不包含 score，因为 SearchResult 模型中的字段类型不匹配
            }
            for item in tavily_results[:max_results]
        ]
        
        logger.info(
            "tavily_api_search_success",
            query=input_data.query,
            results_count=len(results),
            search_depth=search_depth,
            time_range=time_range,
        )
        
        return SearchResult(
            results=results,
            total_found=len(results),
        )
