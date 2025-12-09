"""
DuckDuckGo Search Tool（使用 ddgs 包）

职责：
- 调用 DuckDuckGo API
- 区域和语言配置
- 结果格式化

特点：
- 免费，无需 API Key
- 隐私友好
- 支持多语言和区域
- 使用新包名 ddgs（duckduckgo_search 已重命名）
"""
import asyncio
import time
import structlog
from typing import Dict, List
from collections import deque

from app.tools.base import BaseTool
from app.models.domain import SearchQuery, SearchResult

logger = structlog.get_logger()


class DuckDuckGoSearchTool(BaseTool[SearchQuery, SearchResult]):
    """
    DuckDuckGo 搜索工具
    
    特性：
    - 使用 ddgs 包（duckduckgo_search 的新名称）
    - 支持语言和区域配置
    - 异步执行（通过 asyncio.to_thread）
    - 内置速率控制（避免触发限流）
    """
    
    def __init__(self):
        super().__init__(tool_id="duckduckgo_search")
        
        # 速率控制 - 保守策略
        self._search_semaphore = asyncio.Semaphore(2)  # 最多2个并发请求
        self._last_request_time = 0
        self._min_request_interval = 1.0  # 最小请求间隔1秒
        
        # 滑动窗口速率限制器（每分钟最多30次，保守估计）
        self._request_timestamps = deque()
        self._max_requests_per_minute = 30  # 每分钟最多30次请求
        self._rate_limit_window = 60.0  # 时间窗口60秒
    
    async def _rate_limited_request(self, func):
        """
        带速率限制的请求包装器
        
        功能：
        - 限制并发数量（最多2个）
        - 确保请求间隔（最少1秒）
        - 滑动窗口速率限制（每分钟最多30次）
        - 避免触发API限流
        """
        async with self._search_semaphore:
            now = time.time()
            
            # 第一层：确保最小请求间隔（1秒）
            elapsed = now - self._last_request_time
            if elapsed < self._min_request_interval:
                wait_time = self._min_request_interval - elapsed
                logger.debug(
                    "duckduckgo_rate_limit_min_interval",
                    wait_time=wait_time,
                    elapsed=elapsed
                )
                await asyncio.sleep(wait_time)
                now = time.time()
            
            # 第二层：滑动窗口速率限制（每分钟最多30次）
            cutoff_time = now - self._rate_limit_window
            while self._request_timestamps and self._request_timestamps[0] < cutoff_time:
                self._request_timestamps.popleft()
            
            # 检查是否超过速率限制
            if len(self._request_timestamps) >= self._max_requests_per_minute:
                oldest_timestamp = self._request_timestamps[0]
                wait_time = oldest_timestamp + self._rate_limit_window - now
                
                if wait_time > 0:
                    logger.warning(
                        "duckduckgo_rate_limit_per_minute_throttle",
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
            
            # 执行搜索
            result = await asyncio.to_thread(func)
            
            # 记录请求时间
            self._last_request_time = time.time()
            self._request_timestamps.append(self._last_request_time)
            
            logger.debug(
                "duckduckgo_request_executed",
                requests_in_last_minute=len(self._request_timestamps),
                max_requests=self._max_requests_per_minute
            )
            
            return result
    
    async def execute(self, input_data: SearchQuery) -> SearchResult:
        """
        执行 DuckDuckGo 搜索
        
        Args:
            input_data: 搜索查询
            
        Returns:
            搜索结果
            
        Raises:
            ImportError: 如果 duckduckgo-search 未安装
            Exception: 其他搜索错误
        """
        try:
            # 动态导入 ddgs（新包名）
            from ddgs import DDGS
            
            logger.info(
                "duckduckgo_search_start",
                query=input_data.query,
                max_results=input_data.max_results,
                language=input_data.language,
            )
            
            # DuckDuckGo 搜索是同步的，需要在线程池中执行
            def _sync_search():
                with DDGS() as ddgs:
                    # 根据语言选择搜索区域
                    region = None
                    if input_data.language:
                        # 语言映射到区域
                        lang_to_region = {
                            "zh": "cn-zh",  # 中国
                            "en": "us-en",  # 美国
                            "ja": "jp-ja",  # 日本
                            "ko": "kr-ko",  # 韩国
                        }
                        region = lang_to_region.get(input_data.language.lower())
                    
                    # 执行搜索
                    # 注意：ddgs.text() 第一个参数是位置参数 query，不是 keywords
                    search_results = ddgs.text(
                        input_data.query,  # 第一个位置参数是 query
                        max_results=input_data.max_results,
                        region=region,
                    )
                    
                    # 转换结果格式
                    results = []
                    for item in search_results:
                        results.append({
                            "title": item.get("title", ""),
                            "url": item.get("href", ""),
                            "snippet": item.get("body", "")[:200],  # 截取前200字符
                            "published_date": "",  # DuckDuckGo 不提供发布日期
                        })
                    
                    return results
            
            # 在线程池中执行同步搜索（带速率限制）
            results = await self._rate_limited_request(_sync_search)
            
            logger.info(
                "duckduckgo_search_success",
                query=input_data.query,
                results_count=len(results),
            )
            
            return SearchResult(
                results=results,
                total_found=len(results),
            )
            
        except ImportError:
            logger.error(
                "duckduckgo_search_import_error",
                error="ddgs 未安装"
            )
            raise ValueError("DuckDuckGo 搜索需要安装 ddgs 库（pip install ddgs）")
        except Exception as e:
            logger.error(
                "duckduckgo_search_failed",
                query=input_data.query,
                error=str(e)
            )
            raise

