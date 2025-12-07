"""
全局依赖项管理（已重构）

使用新的模块化架构：
- OrchestratorFactory 管理组件创建
- WorkflowExecutor 替代原有的 RoadmapOrchestrator
"""
import asyncio
import structlog
from app.core.orchestrator_factory import (
    OrchestratorFactory,
    get_workflow_executor as _get_workflow_executor,
)
from app.core.orchestrator.executor import WorkflowExecutor
from app.db.repository_factory import RepositoryFactory

logger = structlog.get_logger()


async def init_orchestrator():
    """
    初始化 Orchestrator（在应用启动时调用）
    
    流程：
    1. 初始化 OrchestratorFactory（创建 Checkpointer 和 StateManager）
    2. 记录初始化成功
    """
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
    清理 Orchestrator（在应用关闭时调用）
    
    流程：
    1. 关闭 PostgreSQL 连接池
    2. 清空全局实例
    """
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


# 向后兼容：保留旧的函数名
def get_orchestrator() -> WorkflowExecutor:
    """
    【已废弃】向后兼容函数，请使用 get_workflow_executor()
    
    Returns:
        WorkflowExecutor 实例
    """
    return get_workflow_executor()


def get_repository_factory() -> RepositoryFactory:
    """
    获取 RepositoryFactory 实例
    
    用作 FastAPI 依赖注入：
        repo_factory: RepositoryFactory = Depends(get_repository_factory)
    
    Returns:
        RepositoryFactory 实例（每次调用创建新实例）
    """
    logger.debug("repository_factory_created")
    return RepositoryFactory()
