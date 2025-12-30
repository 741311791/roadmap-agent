"""
Tavily API Search Tool（使用全局速率限制器）

职责：
- 使用官方 TavilyClient（同步客户端）
- 从数据库读取配额信息，选择最优 Key
- 支持完整的 API 参数（search_depth, time_range, include_domains 等）
- 全局速率控制（每分钟 100 次，基于 Redis）
- 结果格式化

不负责：
- 回退逻辑（由 Router 处理）
- 配额追踪和健康检查（由外部项目维护）

官方文档：https://github.com/tavily-ai/tavily-python
"""
import asyncio
import time
import structlog
from typing import Dict, Optional

from tavily import TavilyClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool
from app.models.domain import SearchQuery, SearchResult
from app.db.repositories.tavily_key_repo import TavilyKeyRepository
from app.utils.rate_limiter import get_tavily_rate_limiter

logger = structlog.get_logger()


class TavilyAPISearchTool(BaseTool[SearchQuery, SearchResult]):
    """
    Tavily API 搜索工具（使用全局速率限制器）
    
    特性：
    - 使用官方 TavilyClient（按照官方示例调用）
    - 从数据库读取配额信息（由外部项目维护）
    - 全局速率控制（每分钟 100 次，基于 Redis，多进程共享）
    - 支持高级搜索参数（search_depth, time_range, include_domains 等）
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        初始化搜索工具
        
        Args:
            db_session: 数据库会话（用于查询 API Key）
        """
        super().__init__(tool_id="tavily_api_search")
        
        # 数据库仓储
        self.repo = TavilyKeyRepository(db_session)
        
        # TavilyClient 缓存（按 API Key 索引）
        self._clients: Dict[str, TavilyClient] = {}
        
        # 局部并发控制（防止单个实例过度并发）
        self._search_semaphore = asyncio.Semaphore(3)  # 最多3个并发请求
    
    def _get_client(self, api_key: str) -> TavilyClient:
        """
        获取或创建指定 Key 的 TavilyClient 实例
        
        Args:
            api_key: API Key
            
        Returns:
            TavilyClient 实例
        """
        if api_key not in self._clients:
            self._clients[api_key] = TavilyClient(api_key=api_key)
            logger.debug(
                "tavily_client_created",
                key_prefix=api_key[:10] + "..."
            )
        return self._clients[api_key]
    
    async def _rate_limited_request(self, func, *args, **kwargs):
        """
        带全局速率限制的请求包装器
        
        功能：
        - 局部并发控制（最多3个并发，防止单实例过载）
        - 全局速率限制（每分钟100次，基于 Redis，多进程共享）
        - 避免触发 API 限流
        - 使用 asyncio.to_thread 包装同步调用
        """
        # 获取全局速率限制器
        rate_limiter = await get_tavily_rate_limiter()
        
        # 局部并发控制
        async with self._search_semaphore:
            # 全局速率限制（会自动等待直到有配额）
            try:
                await rate_limiter.acquire(timeout=30.0)  # 最多等待 30 秒
            except TimeoutError as e:
                logger.error(
                    "tavily_api_rate_limit_timeout",
                    message=str(e),
                )
                raise ValueError("Tavily API rate limit exceeded, please try again later")
            
            # 使用 asyncio.to_thread 在线程中执行同步调用
            result = await asyncio.to_thread(func, *args, **kwargs)
            
            # 记录请求执行（用于监控）
            current_count = await rate_limiter.get_current_count()
            logger.debug(
                "tavily_api_request_executed",
                requests_in_last_minute=current_count,
                max_requests=100,
            )
            
            return result
    
    async def _get_best_key(self) -> Optional[str]:
        """
        从数据库获取最优 API Key
        
        Returns:
            API Key 字符串，如果没有可用 Key 则返回 None
        """
        key_record = await self.repo.get_best_key()
        if key_record:
            return key_record.api_key
        return None
    
    async def execute(self, input_data: SearchQuery) -> SearchResult:
        """
        执行 Tavily API 搜索
        
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
            ValueError: 如果没有可用的 API Key
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
        )
        
        # 获取最优 API Key
        api_key = await self._get_best_key()
        
        if not api_key:
            error_msg = "没有可用的 Tavily API Key（数据库中无配额充足的 Key）"
            logger.error(
                "tavily_no_available_key",
                query=input_data.query,
            )
            raise ValueError(error_msg)
        
        logger.info(
            "tavily_search_using_key",
            query=input_data.query,
            key_prefix=api_key[:10] + "...",
        )
        
        try:
            # 执行搜索
            def do_search():
                """执行搜索（同步调用，按照官方示例）"""
                client = self._get_client(api_key)
                
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
                key_prefix=api_key[:10] + "...",
            )
            
            return SearchResult(
                results=results,
                total_found=len(results),
            )
            
        except Exception as e:
            logger.error(
                "tavily_api_search_failed",
                query=input_data.query,
                key_prefix=api_key[:10] + "...",
                error=str(e)[:200],
                error_type=type(e).__name__,
            )
            raise
