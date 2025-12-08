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
import structlog
from typing import Dict, List

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
    """
    
    def __init__(self):
        super().__init__(tool_id="duckduckgo_search")
    
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

