"""
全局依赖项管理（已重构）

使用新的模块化架构：
- OrchestratorFactory 管理组件创建
- WorkflowExecutor 替代原有的 RoadmapOrchestrator
- Redis 客户端管理缓存和会话
"""
import asyncio
import structlog
from app.core.orchestrator_factory import (
    OrchestratorFactory,
    get_workflow_executor as _get_workflow_executor,
)
from app.core.orchestrator.executor import WorkflowExecutor
from app.db.redis_client import redis_client

logger = structlog.get_logger()


async def init_orchestrator():
    """
    初始化 Orchestrator 和 Redis（在应用启动时调用）
    
    流程：
    1. 初始化 Redis 客户端
    2. 初始化 OrchestratorFactory（创建 Checkpointer 和 StateManager）
    3. 记录初始化成功
    """
    logger.info("services_initializing")
    
    # 初始化 Redis 客户端
    try:
        await redis_client.connect()
        # 测试连接
        await redis_client.ping()
        logger.info("redis_client_connected")
    except Exception as e:
        logger.error(
            "redis_connection_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        # Redis 连接失败不应阻止应用启动（降级运行）
        logger.warning("redis_unavailable_running_in_degraded_mode")
    
    # 初始化 Orchestrator
    logger.info("orchestrator_initializing")
    
    try:
        await asyncio.wait_for(
            OrchestratorFactory.initialize(),
            timeout=30.0
        )
        
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
    清理 Orchestrator 和 Redis（在应用关闭时调用）
    
    流程：
    1. 关闭 Redis 连接
    2. 关闭 PostgreSQL 连接池
    3. 清空全局实例
    """
    # 关闭 Redis 连接
    try:
        await redis_client.close()
        logger.info("redis_client_closed")
    except Exception as e:
        logger.warning("redis_cleanup_error", error=str(e))
    
    # 关闭 Orchestrator
    try:
        await OrchestratorFactory.cleanup()
        logger.info("orchestrator_shutdown_completed")
    except Exception as e:
        logger.warning("orchestrator_cleanup_error", error=str(e))
    finally:
        logger.info("orchestrator_cleaned_up")


def get_workflow_executor() -> WorkflowExecutor:
    """
    获取 WorkflowExecutor 实例
    
    用作 FastAPI 依赖注入：
        executor: WorkflowExecutor = Depends(get_workflow_executor)
    
    Returns:
        WorkflowExecutor 实例（每次调用创建新实例，但共享 StateManager 和 Checkpointer）
    """
    return _get_workflow_executor()
