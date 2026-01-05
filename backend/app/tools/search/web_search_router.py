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
from app.db.session import get_db

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
    1. Tavily API - 高质量搜索结果（从数据库读取配额）
    2. DuckDuckGo - 免费备选方案（如果启用）
    """
    
    def __init__(self):
        super().__init__(tool_id="web_search_v1")
        
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
    
    async def _has_valid_tavily_keys(self, db_session: AsyncSession) -> bool:
        """
        检查数据库中是否有可用的 Tavily API Key
        
        Args:
            db_session: 数据库会话
            
        Returns:
            True 如果有可用的 Key
            
        注意：
        - 在高并发场景下，此方法可能导致连接池耗尽
        - 如果查询超时，快速失败并返回 False
        """
        try:
            import asyncio
            from app.db.repositories.tavily_key_repo import TavilyKeyRepository
            
            repo = TavilyKeyRepository(db_session)
            
            # 设置超时保护（5秒），避免在连接池耗尽时长时间阻塞
            key_record = await asyncio.wait_for(
                repo.get_best_key(),
                timeout=5.0
            )
            return key_record is not None
            
        except asyncio.TimeoutError:
            # 连接池耗尽或数据库响应慢，快速失败
            logger.warning(
                "web_search_router_tavily_check_timeout",
                message="Tavily Key 查询超时（可能是连接池耗尽），回退到 DuckDuckGo"
            )
            return False
        except Exception as e:
            # 其他错误（包括连接池 TimeoutError）
            error_msg = str(e).lower()
            if "pool" in error_msg or "timeout" in error_msg:
                logger.warning(
                    "web_search_router_tavily_check_pool_exhausted",
                    error=str(e)[:200],
                    message="连接池耗尽，跳过 Tavily 检查"
                )
            else:
                logger.warning(
                    "web_search_router_tavily_check_failed",
                    error=str(e)[:200]
                )
            return False
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    async def execute(
        self, 
        input_data: SearchQuery, 
        db_session: Optional[AsyncSession] = None,
        pre_allocated_tavily_key: Optional[str] = None
    ) -> SearchResult:
        """
        执行网络搜索（按优先级路由）
        
        优先级：
        1. Tavily API（使用预分配 Key 或从数据库读取配额）
        2. DuckDuckGo（如果启用了 fallback）
        
        Args:
            input_data: 搜索查询
            db_session: 数据库会话（用于 Tavily API Key 查询，仅在未提供预分配 Key 时使用）
            pre_allocated_tavily_key: 预分配的 Tavily API Key（如果提供，跳过数据库查询）
            
        Returns:
            搜索结果
            
        Raises:
            ValueError: 如果所有搜索引擎都不可用或都失败
        """
        # 模式 1：使用预分配的 Tavily Key（优化路径）
        if pre_allocated_tavily_key:
            try:
                logger.info(
                    "web_search_router_trying_tavily_with_pre_allocated_key",
                    query=input_data.query,
                    key_prefix=pre_allocated_tavily_key[:10] + "...",
                )
                # 使用预分配 Key 创建 TavilyAPISearchTool（跳过数据库查询）
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
                    "web_search_router_tavily_pre_allocated_failed",
                    query=input_data.query,
                    error=str(e),
                    message="预分配 Tavily Key 失败，尝试回退到 DuckDuckGo"
                )
                
                # 回退到 DuckDuckGo（如果可用）
                if self.duckduckgo_tool:
                    try:
                        logger.info(
                            "web_search_router_fallback_to_duckduckgo",
                            query=input_data.query,
                            reason="预分配 Tavily Key 失败"
                        )
                        result = await self.duckduckgo_tool.execute(input_data)
                        logger.info(
                            "web_search_router_success",
                            query=input_data.query,
                            engine="duckduckgo",
                            results_count=result.total_found,
                        )
                        return result
                    except Exception as ddg_error:
                        logger.error(
                            "web_search_router_all_engines_failed",
                            query=input_data.query,
                            tavily_error=str(e),
                            duckduckgo_error=str(ddg_error),
                        )
                        raise ValueError(
                            f"所有搜索引擎都失败: Tavily={e}, DuckDuckGo={ddg_error}"
                        )
                else:
                    # 没有备选方案
                    raise
        
        # 模式 2：从数据库查询 Key（原有行为）
        # 如果没有提供数据库会话，尝试获取一个
        if db_session is None:
            async for session in get_db():
                db_session = session
                break
        
        tavily_available = await self._has_valid_tavily_keys(db_session)
        
        logger.info(
            "web_search_router_start",
            query=input_data.query,
            max_results=input_data.max_results,
            tavily_available=tavily_available,
            duckduckgo_available=self.duckduckgo_tool is not None,
        )
        
        # 策略 1: 尝试使用 Tavily API（从数据库查询 Key）
        if tavily_available:
            try:
                logger.info(
                    "web_search_router_trying_tavily",
                    query=input_data.query
                )
                # 动态创建 TavilyAPISearchTool 实例（传递数据库会话）
                tavily_tool = TavilyAPISearchTool(db_session=db_session)
                result = await tavily_tool.execute(input_data)
                
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
            tavily_configured=tavily_available,
            duckduckgo_enabled=settings.USE_DUCKDUCKGO_FALLBACK,
        )
        raise ValueError(error_msg)

