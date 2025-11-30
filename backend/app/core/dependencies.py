"""
全局依赖项管理
"""
import asyncio
import structlog
from app.core.orchestrator import RoadmapOrchestrator

logger = structlog.get_logger()

# 全局 orchestrator 实例（单例）
_orchestrator: RoadmapOrchestrator | None = None


async def init_orchestrator():
    """
    初始化全局 orchestrator 实例（在应用启动时调用）
    
    流程：
    1. 调用 RoadmapOrchestrator.initialize() 初始化连接池和 checkpointer
    2. 创建 RoadmapOrchestrator 实例
    3. 记录初始化成功
    """
    global _orchestrator
    
    logger.info("orchestrator_initializing")
    
    try:
        # 初始化 Orchestrator 类级别资源（连接池、checkpointer）
        await asyncio.wait_for(
            RoadmapOrchestrator.initialize(),
            timeout=30.0
        )
        
        # 创建实例
        _orchestrator = RoadmapOrchestrator()
        
        logger.info("orchestrator_initialized", checkpointer_type="AsyncPostgresSaver")
        
    except asyncio.TimeoutError:
        logger.error(
            "postgres_connection_timeout",
            timeout_seconds=30,
            message="PostgreSQL 连接超时，请检查数据库服务是否可用"
        )
        raise RuntimeError(
            "PostgreSQL 连接超时（30秒）。"
            "请检查：1) PostgreSQL 服务是否运行 2) POSTGRES_* 配置是否正确 3) 网络连接是否正常"
        )
    except Exception as e:
        logger.error(
            "orchestrator_initialization_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


async def cleanup_orchestrator():
    """
    清理 orchestrator（在应用关闭时调用）
    
    流程：
    1. 关闭 PostgreSQL 连接池
    2. 清空全局实例
    """
    global _orchestrator
    
    try:
        # 关闭类级别资源
        await RoadmapOrchestrator.shutdown()
        logger.info("orchestrator_shutdown_completed")
    except Exception as e:
        logger.warning("orchestrator_cleanup_error", error=str(e))
    finally:
        _orchestrator = None
        logger.info("orchestrator_cleaned_up")


def get_orchestrator() -> RoadmapOrchestrator:
    """
    获取全局 orchestrator 实例
    
    用作 FastAPI 依赖注入：
        orchestrator: RoadmapOrchestrator = Depends(get_orchestrator)
    """
    if _orchestrator is None:
        raise RuntimeError("Orchestrator 尚未初始化，请确保应用已正确启动")
    return _orchestrator
