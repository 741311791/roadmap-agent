"""
Web Search Tool（支持 Tavily API 和 DuckDuckGo 备选）
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
import structlog
from typing import List, Dict
import asyncio

from app.tools.base import BaseTool
from app.models.domain import SearchQuery, SearchResult
from app.config.settings import settings

logger = structlog.get_logger()


class WebSearchTool(BaseTool[SearchQuery, SearchResult]):
    """
    Web 搜索工具
    
    搜索引擎优先级：
    1. Tavily API（主要）：高质量搜索结果，需要 API Key
    2. DuckDuckGo（备选）：免费，无需 API Key，隐私友好
    """
    
    def __init__(self):
        super().__init__(tool_id="web_search_v1")
        self.api_key = settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com"
        self.use_duckduckgo_fallback = settings.USE_DUCKDUCKGO_FALLBACK
    
    async def _search_with_tavily(self, input_data: SearchQuery) -> SearchResult:
        """
        使用 Tavily API 搜索
        
        Args:
            input_data: 搜索查询
            
        Returns:
            搜索结果
            
        Raises:
            Exception: 搜索失败时抛出异常
        """
        if not self.api_key:
            raise ValueError("Tavily API Key 未配置")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/search",
                json={
                    "api_key": self.api_key,
                    "query": input_data.query,
                    "search_depth": "basic",  # basic, advanced
                    "max_results": input_data.max_results,
                    "include_answer": False,
                    "include_raw_content": False,
                    "include_images": False,
                },
                headers={
                    "Content-Type": "application/json",
                },
                timeout=15.0,
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Tavily 返回格式：{"results": [{"title", "url", "content", "score", "published_date"}], ...}
            tavily_results = data.get("results", [])
            
            results = [
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", "")[:200],  # 截取前200字符作为摘要
                    "published_date": item.get("published_date", ""),
                }
                for item in tavily_results[:input_data.max_results]
            ]
            
            logger.info(
                "web_search_tavily_success",
                query=input_data.query,
                results_count=len(results),
            )
            
            return SearchResult(
                results=results,
                total_found=len(results),
            )
    
    async def _search_with_duckduckgo(self, input_data: SearchQuery) -> SearchResult:
        """
        使用 DuckDuckGo 搜索（备选方案）
        
        Args:
            input_data: 搜索查询
            
        Returns:
            搜索结果
        """
        try:
            # 动态导入 duckduckgo_search（避免在导入时失败）
            from duckduckgo_search import DDGS
            
            # DuckDuckGo 搜索是同步的，需要在线程池中执行
            def _sync_search():
                with DDGS() as ddgs:
                    # 根据内容类型选择搜索区域
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
                    search_results = ddgs.text(
                        keywords=input_data.query,
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
            
            # 在线程池中执行同步搜索
            results = await asyncio.to_thread(_sync_search)
            
            logger.info(
                "web_search_duckduckgo_success",
                query=input_data.query,
                results_count=len(results),
            )
            
            return SearchResult(
                results=results,
                total_found=len(results),
            )
            
        except ImportError:
            logger.error("web_search_duckduckgo_import_error", error="duckduckgo-search 未安装")
            raise ValueError("DuckDuckGo 搜索需要安装 duckduckgo-search 库")
        except Exception as e:
            logger.error("web_search_duckduckgo_failed", error=str(e))
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def execute(self, input_data: SearchQuery) -> SearchResult:
        """
        执行网络搜索
        
        优先使用 Tavily API，失败时回退到 DuckDuckGo（如果启用）
        
        Args:
            input_data: 搜索查询
            
        Returns:
            搜索结果
        """
        # 尝试使用 Tavily（如果配置了 API Key）
        if self.api_key:
            try:
                return await self._search_with_tavily(input_data)
            except Exception as e:
                logger.warning(
                    "web_search_tavily_failed",
                    error=str(e),
                    query=input_data.query,
                )
                
                # 如果启用了 DuckDuckGo 备选，则回退
                if self.use_duckduckgo_fallback:
                    logger.info(
                        "web_search_fallback_to_duckduckgo",
                        query=input_data.query,
                    )
                    try:
                        return await self._search_with_duckduckgo(input_data)
                    except Exception as fallback_error:
                        logger.error(
                            "web_search_all_providers_failed",
                            tavily_error=str(e),
                            duckduckgo_error=str(fallback_error),
                        )
                        raise ValueError(f"所有搜索引擎都失败: Tavily={e}, DuckDuckGo={fallback_error}")
                else:
                    # 未启用备选，直接抛出异常
                    raise
        
        # 没有配置 Tavily API Key，直接使用 DuckDuckGo
        if self.use_duckduckgo_fallback:
            logger.info(
                "web_search_using_duckduckgo_only",
                query=input_data.query,
                reason="Tavily API Key 未配置",
            )
            return await self._search_with_duckduckgo(input_data)
        else:
            raise ValueError("未配置 Tavily API Key 且未启用 DuckDuckGo 备选")

