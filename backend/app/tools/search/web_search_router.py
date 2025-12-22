"""
Web Search Router（搜索工具路由器）

职责：
- 按优先级选择搜索引擎
- 处理回退逻辑
- 统一错误处理

优先级：
1. Tavily API（如果配置了 API Key）
2. DuckDuckGo（如果启用了 fallback）
"""
import structlog
from tenacity import retry, stop_after_attempt, wait_fixed

from app.tools.base import BaseTool
from app.models.domain import SearchQuery, SearchResult
from app.config.settings import settings
from app.tools.search.tavily_api_search import TavilyAPISearchTool
from app.tools.search.duckduckgo_search import DuckDuckGoSearchTool

logger = structlog.get_logger()


class WebSearchRouter(BaseTool[SearchQuery, SearchResult]):
    """
    Web 搜索路由工具
    
    特性：
    - 集中管理搜索引擎选择逻辑
    - 自动回退机制（Tavily → DuckDuckGo）
    - 统一的错误处理和日志
    - 易于扩展新的搜索引擎
    
    优先级策略：
    1. Tavily API - 高质量搜索结果（需要 API Key）
    2. DuckDuckGo - 免费备选方案（如果启用）
    """
    
    def __init__(self):
        super().__init__(tool_id="web_search_v1")
        
        # 初始化搜索工具
        self.tavily_tool = None
        self.duckduckgo_tool = None
        
        # 尝试初始化 Tavily API 工具
        try:
            self.tavily_tool = TavilyAPISearchTool()
        except Exception as e:
            logger.warning(
                "web_search_router_tavily_init_failed",
                error=str(e),
                message="Tavily API 工具初始化失败，将跳过 Tavily"
            )
        
        # 尝试初始化 DuckDuckGo 工具
        if settings.USE_DUCKDUCKGO_FALLBACK:
            try:
                self.duckduckgo_tool = DuckDuckGoSearchTool()
            except Exception as e:
                logger.warning(
                    "web_search_router_duckduckgo_init_failed",
                    error=str(e),
                    message="DuckDuckGo 工具初始化失败"
                )
    
    def _has_valid_tavily_config(self) -> bool:
        """
        检查是否有有效的 Tavily API 配置
        
        Returns:
            True 如果 Tavily API 可用
        """
        if not self.tavily_tool:
            return False
        
        # 检查 TavilyAPIKeyManager 是否有可用的 API keys
        try:
            return (
                hasattr(self.tavily_tool, 'key_manager') and 
                self.tavily_tool.key_manager is not None and
                len(self.tavily_tool.key_manager.api_keys) > 0
            )
        except Exception as e:
            logger.warning(
                "web_search_router_tavily_config_check_failed",
                error=str(e)
            )
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def execute(self, input_data: SearchQuery) -> SearchResult:
        """
        执行网络搜索（按优先级路由）
        
        优先级：
        1. Tavily API（如果配置了 API Key）
        2. DuckDuckGo（如果启用了 fallback）
        
        Args:
            input_data: 搜索查询
            
        Returns:
            搜索结果
            
        Raises:
            ValueError: 如果所有搜索引擎都不可用或都失败
        """
        logger.info(
            "web_search_router_start",
            query=input_data.query,
            max_results=input_data.max_results,
            tavily_available=self._has_valid_tavily_config(),
            duckduckgo_available=self.duckduckgo_tool is not None,
        )
        
        # 策略 1: 尝试使用 Tavily API
        if self._has_valid_tavily_config():
            try:
                logger.info(
                    "web_search_router_trying_tavily",
                    query=input_data.query
                )
                result = await self.tavily_tool.execute(input_data)
                
                logger.info(
                    "web_search_router_success",
                    query=input_data.query,
                    engine="tavily",
                    results_count=result.total_found,
                )
                return result
                
            except Exception as e:
                logger.warning(
                    "web_search_router_tavily_failed",
                    query=input_data.query,
                    error=str(e),
                    message="Tavily API 失败，尝试回退到 DuckDuckGo"
                )
                
                # 如果启用了 DuckDuckGo 备选，继续尝试
                if not self.duckduckgo_tool:
                    # 没有备选方案，直接抛出异常
                    raise
        
        # 策略 2: 使用 DuckDuckGo（备选方案）
        if self.duckduckgo_tool:
            try:
                logger.info(
                    "web_search_router_trying_duckduckgo",
                    query=input_data.query,
                    reason="Tavily 不可用或失败"
                )
                result = await self.duckduckgo_tool.execute(input_data)
                
                logger.info(
                    "web_search_router_success",
                    query=input_data.query,
                    engine="duckduckgo",
                    results_count=result.total_found,
                )
                return result
                
            except Exception as duckduckgo_error:
                logger.error(
                    "web_search_router_all_engines_failed",
                    query=input_data.query,
                    duckduckgo_error=str(duckduckgo_error),
                )
                raise ValueError(
                    f"所有搜索引擎都失败: DuckDuckGo={duckduckgo_error}"
                )
        
        # 没有任何可用的搜索引擎
        error_msg = "未配置任何可用的搜索引擎"
        logger.error(
            "web_search_router_no_engines_available",
            query=input_data.query,
            tavily_configured=self._has_valid_tavily_config(),
            duckduckgo_enabled=settings.USE_DUCKDUCKGO_FALLBACK,
        )
        raise ValueError(error_msg)

