"""
Web Search Tool（基于 Tavily API）
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_fixed
import structlog

from app.tools.base import BaseTool
from app.models.domain import SearchQuery, SearchResult
from app.config.settings import settings

logger = structlog.get_logger()


class WebSearchTool(BaseTool[SearchQuery, SearchResult]):
    """Web 搜索工具（使用 Tavily API）"""
    
    def __init__(self):
        super().__init__(tool_id="web_search_v1")
        self.api_key = settings.TAVILY_API_KEY
        self.base_url = "https://api.tavily.com"
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def execute(self, input_data: SearchQuery) -> SearchResult:
        """
        执行网络搜索（使用 Tavily API）
        
        Args:
            input_data: 搜索查询
            
        Returns:
            搜索结果
        """
        async with httpx.AsyncClient() as client:
            try:
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
                    "web_search_success",
                    query=input_data.query,
                    results_count=len(results),
                    provider="tavily",
                )
                
                return SearchResult(
                    results=results,
                    total_found=len(results),
                )
                
            except httpx.HTTPError as e:
                logger.error("web_search_failed", error=str(e), provider="tavily")
                raise
            except KeyError as e:
                logger.error("web_search_response_format_error", error=str(e), provider="tavily")
                raise ValueError(f"Tavily API 响应格式错误: {e}")

