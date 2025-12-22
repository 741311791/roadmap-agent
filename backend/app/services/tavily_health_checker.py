"""
Tavily API Key 健康检查服务

职责：
- 定期检查所有 API Keys 的健康状态
- 执行轻量级测试搜索
- 更新 Redis 中的健康状态
- 在后台持续运行

设计原则：
- 非阻塞：使用 asyncio.create_task 在后台运行
- 容错：健康检查失败不影响主应用
- 日志友好：记录详细的检查结果
"""
import asyncio
import structlog
from typing import Optional

from app.config.settings import settings
from app.db.redis_client import get_redis_client
from app.tools.search.tavily_key_manager import TavilyAPIKeyManager
from app.models.domain import SearchQuery
from tavily import TavilyClient

logger = structlog.get_logger()


class TavilyHealthCheckService:
    """
    Tavily API Key 健康检查服务
    
    特性：
    - 每 5 分钟执行一次健康检查
    - 使用轻量级搜索测试 Key 的可用性
    - 记录响应时间和成功状态
    - 更新 Redis 中的健康状态
    """
    
    def __init__(self):
        """初始化健康检查服务"""
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self._check_interval = 300  # 5 分钟（秒）
        
        # 获取 API Keys
        api_keys = settings.get_tavily_api_keys
        if not api_keys:
            logger.warning(
                "tavily_health_checker_no_keys",
                message="未配置 Tavily API Keys，健康检查服务将不会启动"
            )
            self.key_manager = None
            return
        
        # 初始化 Key Manager
        self.key_manager = TavilyAPIKeyManager(
            redis_client=get_redis_client(),
            api_keys=api_keys
        )
        
        logger.info(
            "tavily_health_checker_initialized",
            total_keys=len(api_keys),
            check_interval_seconds=self._check_interval,
        )
    
    async def _check_single_key(self, key_index: int) -> bool:
        """
        检查单个 Key 的健康状态
        
        策略：
        - 执行一次轻量级搜索（search_depth=basic, max_results=1）
        - 记录响应时间
        - 返回是否成功
        
        Args:
            key_index: Key 索引
            
        Returns:
            True 表示健康，False 表示不健康
        """
        api_key = self.key_manager.api_keys[key_index]
        key_id = self.key_manager._get_key_id(key_index)
        
        try:
            # 创建临时 TavilyClient
            client = TavilyClient(api_key=api_key)
            
            # 执行轻量级测试搜索
            import time
            start_time = time.time()
            
            # 使用简单的测试查询
            result = await asyncio.to_thread(
                client.search,
                query="test",
                search_depth="basic",
                max_results=1
            )
            
            elapsed_time = time.time() - start_time
            
            # 检查结果是否有效
            if result and isinstance(result, dict):
                logger.info(
                    "tavily_health_check_success",
                    key_index=key_index,
                    key_id=key_id,
                    response_time_ms=round(elapsed_time * 1000, 2),
                )
                return True
            else:
                logger.warning(
                    "tavily_health_check_invalid_response",
                    key_index=key_index,
                    key_id=key_id,
                )
                return False
                
        except Exception as e:
            error_str = str(e).lower()
            
            # 限流错误不一定表示 Key 不健康，只是暂时不可用
            if "rate limit" in error_str or "429" in error_str:
                logger.info(
                    "tavily_health_check_rate_limited",
                    key_index=key_index,
                    key_id=key_id,
                    message="Key 遇到限流，但仍然有效"
                )
                # 限流不算不健康
                return True
            else:
                logger.warning(
                    "tavily_health_check_failed",
                    key_index=key_index,
                    key_id=key_id,
                    error=str(e)[:200],
                )
                return False
    
    async def _run_health_check_cycle(self):
        """
        运行一轮健康检查（检查所有 Keys）
        """
        if not self.key_manager:
            return
        
        logger.info(
            "tavily_health_check_cycle_start",
            total_keys=len(self.key_manager.api_keys)
        )
        
        healthy_count = 0
        unhealthy_count = 0
        
        # 并发检查所有 Keys
        tasks = [
            self._check_single_key(idx)
            for idx in range(len(self.key_manager.api_keys))
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 更新健康状态
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "tavily_health_check_exception",
                    key_index=idx,
                    error=str(result),
                )
                unhealthy_count += 1
                await self.key_manager._mark_key_unhealthy(idx)
            elif result:
                healthy_count += 1
                await self.key_manager._mark_key_healthy(idx)
            else:
                unhealthy_count += 1
                await self.key_manager._mark_key_unhealthy(idx)
        
        logger.info(
            "tavily_health_check_cycle_complete",
            total_keys=len(self.key_manager.api_keys),
            healthy=healthy_count,
            unhealthy=unhealthy_count,
        )
    
    async def _run_background_loop(self):
        """
        后台循环：定期执行健康检查
        """
        logger.info(
            "tavily_health_checker_started",
            check_interval_seconds=self._check_interval
        )
        
        try:
            while self.is_running:
                try:
                    # 执行一轮健康检查
                    await self._run_health_check_cycle()
                except Exception as e:
                    logger.error(
                        "tavily_health_check_cycle_error",
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                
                # 等待下一轮检查
                await asyncio.sleep(self._check_interval)
                
        except asyncio.CancelledError:
            logger.info("tavily_health_checker_cancelled")
            raise
        except Exception as e:
            logger.error(
                "tavily_health_checker_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
            )
    
    def start(self):
        """
        启动健康检查服务（非阻塞）
        """
        if not self.key_manager:
            logger.warning(
                "tavily_health_checker_start_skipped",
                reason="未配置 API Keys"
            )
            return
        
        if self.is_running:
            logger.warning(
                "tavily_health_checker_already_running",
                message="健康检查服务已在运行中"
            )
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._run_background_loop())
        
        logger.info(
            "tavily_health_checker_task_created",
            message="健康检查服务已在后台启动"
        )
    
    async def stop(self):
        """
        停止健康检查服务
        """
        if not self.is_running:
            return
        
        logger.info("tavily_health_checker_stopping")
        
        self.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("tavily_health_checker_stopped")


# 全局单例
_health_checker: Optional[TavilyHealthCheckService] = None


def get_health_checker() -> TavilyHealthCheckService:
    """
    获取健康检查服务实例（单例）
    
    Returns:
        TavilyHealthCheckService 实例
    """
    global _health_checker
    
    if _health_checker is None:
        _health_checker = TavilyHealthCheckService()
    
    return _health_checker


async def start_health_checker():
    """
    启动健康检查服务（用于应用启动时调用）
    """
    checker = get_health_checker()
    checker.start()


async def stop_health_checker():
    """
    停止健康检查服务（用于应用关闭时调用）
    """
    checker = get_health_checker()
    await checker.stop()

