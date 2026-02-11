"""
Web Search Router（搜索工具路由器）

职责：
- 按优先级选择搜索引擎
- 处理回退逻辑
- 统一错误处理
- 支持预分配 Tavily API Key（优化性能）

优先级：
1. Tavily API（使用预分配 Key 或从数据库读取配额）
2. DuckDuckGo（如果启用了 fallback）
"""
import structlog
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_fixed
from sqlalchemy.ext.asyncio import AsyncSession

from app.tools.base import BaseTool
from app.models.domain import SearchQuery, SearchResult
from app.config.settings import settings
from app.tools.search.tavily_api_search import TavilyAPISearchTool
from app.tools.search.duckduckgo_search import DuckDuckGoSearchTool

logger = structlog.get_logger()


class WebSearchRouter(BaseTool[SearchQuery, SearchResult]):
    """
    Web 搜索路由工具（已适配统一工具框架）
    
    特性：
    - 集中管理搜索引擎选择逻辑
    - 自动回退机制（Tavily → DuckDuckGo）
    - 统一的错误处理和日志
    - 易于扩展新的搜索引擎
    - 自动生成 LLM Function Schema
    
    优先级策略：
    1. Tavily API - 高质量搜索结果（从 Redis 缓存获取 Key）
    2. DuckDuckGo - 免费备选方案（如果启用）
    """
    
    def __init__(self):
        # ✅ 适配新的 BaseTool 签名
        super().__init__(
            tool_id="web_search_v2",
            name="web_search",  # LLM 调用时使用的名称
            description=(
                "Search the web for up-to-date information. "
                "Use this tool when you need to:\n"
                "- Find current information and recent news\n"
                "- Research specific topics or technologies\n"
                "- Verify facts and statistics\n"
                "- Find learning resources and tutorials\n"
                "- Get latest documentation or API references\n\n"
                "The tool will automatically select the best search engine "
                "(Tavily API or DuckDuckGo) based on availability."
            ),
            args_schema=SearchQuery,  # Pydantic Schema
        )
        
        # DuckDuckGo 工具（无需数据库会话）
        self.duckduckgo_tool = None
        
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
    
    async def _has_valid_tavily_keys_from_cache(self) -> bool:
        """
        从 Redis 缓存检查是否有可用的 Tavily API Key
        
        Returns:
            True 如果缓存中有可用的 Key
            
        优势：
        - 无需数据库连接
        - 性能极高（Redis vs PostgreSQL）
        - 不会导致连接池耗尽
        """
        try:
            from app.core.tavily_key_cache import get_tavily_key_cache
            
            key_cache = get_tavily_key_cache()
            stats = await key_cache.get_cache_stats()
            
            has_keys = stats.get("total_keys", 0) > 0
            
            if not has_keys:
                logger.warning(
                    "web_search_router_tavily_cache_empty",
                    message="Redis 缓存中没有可用的 Tavily Key"
                )
            
            return has_keys
            
        except Exception as e:
            logger.error(
                "web_search_router_tavily_cache_check_failed",
                error=str(e),
            )
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def execute(
        self, 
        input_data: SearchQuery, 
        db_session: Optional[AsyncSession] = None,  # ⚠️ 废弃参数，保留仅为向后兼容
        pre_allocated_tavily_key: Optional[str] = None
    ) -> SearchResult:
        """
        执行网络搜索（按优先级路由）
        
        优先级：
        1. Tavily API（使用预分配 Key 或从 Redis 缓存获取）
        2. DuckDuckGo（如果启用了 fallback）
        
        Args:
            input_data: 搜索查询
            db_session: 废弃参数，保留仅为向后兼容（不再使用）
            pre_allocated_tavily_key: 预分配的 Tavily API Key（如果提供，跳过 Redis 查询）
            
        Returns:
            搜索结果
            
        Raises:
            ValueError: 如果所有搜索引擎都不可用或都失败
            
        架构改进（2026-01-13）：
        - ✅ 移除数据库依赖：直接从 Redis 缓存获取 Key
        - ✅ 提高性能：避免运行时查询数据库
        - ✅ 避免 Session 生命周期问题
        """
        # ============================================================
        # 策略 1: 使用预分配的 Tavily Key（最高优先级）
        # ============================================================
        if pre_allocated_tavily_key:
            try:
                logger.info(
                    "web_search_router_using_pre_allocated_key",
                    query=input_data.query,
                    key_prefix=pre_allocated_tavily_key[:10] + "...",
                )
                tavily_tool = TavilyAPISearchTool(pre_allocated_key=pre_allocated_tavily_key)
                result = await tavily_tool.execute(input_data)
                
                logger.info(
                    "web_search_router_success",
                    query=input_data.query,
                    engine="tavily_pre_allocated",
                    results_count=result.total_found,
                )
                return result
                
            except Exception as e:
                logger.warning(
                    "web_search_router_pre_allocated_key_failed",
                    query=input_data.query,
                    error=str(e),
                )
                # 继续尝试其他策略
        
        # ============================================================
        # 策略 2: 从 Redis 缓存获取 Tavily Key（推荐）
        # ============================================================
        tavily_available = await self._has_valid_tavily_keys_from_cache()
        
        logger.info(
            "web_search_router_start",
            query=input_data.query,
            max_results=input_data.max_results,
            tavily_available=tavily_available,
            duckduckgo_available=self.duckduckgo_tool is not None,
        )
        
        if tavily_available:
            try:
                logger.info(
                    "web_search_router_trying_tavily_from_cache",
                    query=input_data.query
                )
                
                # ✅ 从 Redis 缓存获取 Key（无需数据库连接）
                from app.core.tavily_key_cache import get_tavily_key_cache
                key_cache = get_tavily_key_cache()
                api_key = await key_cache.get_random_key()
                
                if not api_key:
                    logger.warning(
                        "web_search_router_no_key_from_cache",
                        query=input_data.query,
                    )
                    raise ValueError("Redis 缓存中没有可用的 Tavily Key")
                
                # 使用缓存的 Key 创建工具（无需数据库 Session）
                tavily_tool = TavilyAPISearchTool(pre_allocated_key=api_key)
                result = await tavily_tool.execute(input_data)
                
                logger.info(
                    "web_search_router_success",
                    query=input_data.query,
                    engine="tavily_from_cache",
                    results_count=result.total_found,
                )
                return result
                
            except Exception as e:
                logger.warning(
                    "web_search_router_tavily_cache_failed",
                    query=input_data.query,
                    error=str(e),
                )
                # 继续尝试 DuckDuckGo
        
        # ============================================================
        # 策略 3: 使用 DuckDuckGo（备选方案）
        # ============================================================
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
        
        # 所有策略都失败
        error_msg = "所有搜索引擎都不可用或失败"
        logger.error(
            "web_search_router_all_strategies_failed",
            query=input_data.query,
            pre_allocated_key_provided=pre_allocated_tavily_key is not None,
            tavily_cache_available=tavily_available,
            duckduckgo_enabled=settings.USE_DUCKDUCKGO_FALLBACK,
        )
        raise ValueError(error_msg)

