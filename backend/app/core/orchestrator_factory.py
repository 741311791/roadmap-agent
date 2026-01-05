"""
工作流编排器工厂

简化的依赖注入实现，不依赖外部库。
提供单例和工厂函数来创建 Orchestrator 组件。
"""
import structlog
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config.settings import settings
from app.agents.factory import AgentFactory
from app.services.notification_service import notification_service
from app.services.execution_logger import execution_logger
from .orchestrator.base import WorkflowConfig
from .orchestrator.state_manager import StateManager
from .orchestrator.workflow_brain import WorkflowBrain
from .orchestrator.routers import WorkflowRouter
from .orchestrator.builder import WorkflowBuilder
from .orchestrator.executor import WorkflowExecutor
from .orchestrator.node_runners import (
    IntentAnalysisRunner,
    CurriculumDesignRunner,
    ValidationRunner,
    EditorRunner,
    ReviewRunner,
    ContentRunner,
    EditPlanRunner,
)
from .orchestrator.node_runners.validation_edit_plan_runner import ValidationEditPlanRunner

logger = structlog.get_logger()


class OrchestratorFactory:
    """
    工作流编排器工厂
    
    使用单例模式管理共享组件（StateManager, Checkpointer）
    使用连接池来管理数据库连接，防止长时间运行时连接超时。
    """
    
    _state_manager: StateManager | None = None
    _checkpointer: AsyncPostgresSaver | None = None
    _connection_pool: AsyncConnectionPool | None = None
    _agent_factory: AgentFactory | None = None
    _initialized: bool = False
    
    @classmethod
    async def initialize(cls) -> None:
        """
        初始化工厂（应用启动时调用一次）
        
        创建 Checkpointer 和 StateManager 单例。
        使用连接池来管理连接生命周期，防止长时间运行时连接超时。
        """
        if cls._initialized:
            logger.info("orchestrator_factory_already_initialized")
            return
        
        # 创建 StateManager 单例
        cls._state_manager = StateManager()
        
        # 创建 AgentFactory 单例
        cls._agent_factory = AgentFactory(settings)
        
        # 创建 AsyncPostgresSaver（使用连接池，Supabase 优化）
        try:
            # 使用连接池管理连接（PostgreSQL 标准配置）
            # 
            # 连接池参数：
            # - min_size=2: 最小保持 2 个连接（确保基本可用性）
            # - max_size=20: 最大 20 个连接（应对 LangGraph 工作流并发）
            # - max_idle=300: 空闲连接最多保持 5 分钟
            # - timeout=60: 获取连接超时 60 秒
            # - reconnect_timeout=0: 自动重连
            # - open=False: 避免弃用警告，显式调用 await pool.open()
            # 
            # 连接参数（kwargs）：
            # - autocommit=True: 自动提交模式（LangGraph checkpoint 需要）
            # - connect_timeout=30: 连接建立超时 30 秒
            # - keepalives=1: 启用 TCP keepalive（防止长时间空闲连接被中间件断开）
            # - keepalives_idle=30: 空闲 30 秒后开始发送 keepalive 探测
            # - keepalives_interval=10: keepalive 探测间隔 10 秒
            # - keepalives_count=5: 最多 5 次探测失败后关闭连接（总计 50 秒）
            # - options="-c statement_timeout=120000": SQL 语句超时 120 秒（防止长查询阻塞）
            
            # 根据环境动态调整连接池大小
            # 研发环境（ENVIRONMENT=development）：max_size=10
            # 生产环境（ENVIRONMENT=production）：max_size=20
            langgraph_max_size = 10 if settings.ENVIRONMENT == "development" else 20
            
            cls._connection_pool = AsyncConnectionPool(
                conninfo=settings.CHECKPOINTER_DATABASE_URL,
                min_size=2,
                max_size=langgraph_max_size,
                max_idle=300,  # 延长空闲时间到 5 分钟
                timeout=60,
                reconnect_timeout=0,  # 自动重连
                open=False,  # 禁用构造函数自动打开（避免 DeprecationWarning）
                kwargs={
                    "autocommit": True,  # LangGraph checkpoint 需要自动提交
                    "connect_timeout": 30,  # 连接建立超时 30 秒
                    "keepalives": 1,  # 启用 TCP keepalive
                    "keepalives_idle": 30,  # 空闲 30 秒后开始发送 keepalive 探测
                    "keepalives_interval": 10,  # keepalive 探测间隔 10 秒
                    "keepalives_count": 5,  # 最多 5 次探测失败后关闭连接
                    "options": "-c statement_timeout=120000",  # SQL 语句超时 120 秒（120000ms）
                },
            )
            
            logger.info(
                "langgraph_connection_pool_configured",
                environment=settings.ENVIRONMENT,
                max_size=langgraph_max_size,
            )
            
            # 打开连接池
            await cls._connection_pool.open()
            
            # 使用连接池创建 AsyncPostgresSaver
            cls._checkpointer = AsyncPostgresSaver(cls._connection_pool)
            
            # 设置 checkpointer 表
            await cls._checkpointer.setup()
            
            logger.info(
                "orchestrator_factory_initialized",
                checkpointer_type="AsyncPostgresSaver",
                pool_min_size=2,
                pool_max_size=10,
                database_url=settings.CHECKPOINTER_DATABASE_URL.split("@")[-1].split("?")[0],  # 隐藏凭据和参数
            )
            
            cls._initialized = True
            
        except Exception as e:
            logger.error(
                "orchestrator_factory_initialization_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            # 清理已创建的资源
            if cls._connection_pool:
                try:
                    await cls._connection_pool.close()
                except Exception:
                    pass
                cls._connection_pool = None
            raise
    
    @classmethod
    async def cleanup(cls) -> None:
        """清理资源（应用关闭时调用）"""
        # 关闭连接池
        if cls._connection_pool:
            try:
                await cls._connection_pool.close()
                logger.info("orchestrator_factory_pool_closed")
            except Exception as e:
                logger.error(
                    "orchestrator_factory_cleanup_failed",
                    error=str(e),
                )
        
        cls._checkpointer = None
        cls._connection_pool = None
        cls._state_manager = None
        cls._agent_factory = None
        cls._initialized = False
        logger.info("orchestrator_factory_cleaned_up")
    
    @classmethod
    def get_state_manager(cls) -> StateManager:
        """获取 StateManager 单例"""
        if not cls._initialized:
            raise RuntimeError("OrchestratorFactory 未初始化，请先调用 initialize()")
        return cls._state_manager
    
    @classmethod
    def get_checkpointer(cls) -> AsyncPostgresSaver:
        """获取 Checkpointer 单例"""
        if not cls._initialized:
            raise RuntimeError("OrchestratorFactory 未初始化，请先调用 initialize()")
        return cls._checkpointer
    
    @classmethod
    def create_workflow_executor(cls) -> WorkflowExecutor:
        """
        创建 WorkflowExecutor 实例
        
        每次调用都创建新实例，但共享 StateManager 和 Checkpointer。
        
        Returns:
            WorkflowExecutor 实例
        """
        if not cls._initialized:
            raise RuntimeError("OrchestratorFactory 未初始化，请先调用 initialize()")
        
        # 创建配置
        config = WorkflowConfig.from_settings()
        
        # 创建 Router
        router = WorkflowRouter(config)
        
        # 获取共享组件
        state_manager = cls._state_manager
        agent_factory = cls._agent_factory
        
        # 创建 WorkflowBrain（统一协调者）
        brain = WorkflowBrain(
            state_manager=state_manager,
            notification_service=notification_service,
            execution_logger=execution_logger,
        )
        
        # 创建所有 Runners
        # Phase 2 迁移完成: 所有 6 个 Runner 已迁移到使用 WorkflowBrain ✅
        # ✅ ValidationRunner - 已迁移
        # ✅ EditorRunner - 已迁移
        # ✅ ReviewRunner - 已迁移
        # ✅ IntentAnalysisRunner - 已迁移
        # ✅ CurriculumDesignRunner - 已迁移
        # ✅ ContentRunner - 已迁移
        
        intent_runner = IntentAnalysisRunner(brain, agent_factory)  # ← 已迁移
        curriculum_runner = CurriculumDesignRunner(brain, agent_factory)  # ← 已迁移
        validation_runner = ValidationRunner(brain, agent_factory)  # ← 已迁移
        editor_runner = EditorRunner(brain, agent_factory)  # ← 已迁移
        review_runner = ReviewRunner(brain)  # ← 已迁移
        content_runner = ContentRunner(brain)  # ← 已迁移到 Celery
        edit_plan_runner = EditPlanRunner(brain, agent_factory)  # 修改计划分析节点（人工审核触发）
        validation_edit_plan_runner = ValidationEditPlanRunner(brain, agent_factory)  # 验证结果修改计划分析节点（验证失败触发）
        
        # 创建 Builder
        builder = WorkflowBuilder(
            config=config,
            router=router,
            intent_runner=intent_runner,
            curriculum_runner=curriculum_runner,
            validation_runner=validation_runner,
            editor_runner=editor_runner,
            review_runner=review_runner,
            content_runner=content_runner,
            edit_plan_runner=edit_plan_runner,
            validation_edit_plan_runner=validation_edit_plan_runner,  # 新增
        )
        
        # 创建 Executor
        executor = WorkflowExecutor(
            builder=builder,
            state_manager=state_manager,
            checkpointer=cls._checkpointer,
            execution_logger=execution_logger,  # 关键修复：传递 execution_logger
        )
        
        logger.info(
            "workflow_executor_created",
            brain_created=True,
            runners_count=8,  # 包含 EditPlanRunner 和 ValidationEditPlanRunner
        )
        
        return executor


# 便捷函数（保持向后兼容）
async def initialize_orchestrator() -> None:
    """初始化 Orchestrator（应用启动时调用）"""
    await OrchestratorFactory.initialize()


async def cleanup_orchestrator() -> None:
    """清理 Orchestrator 资源（应用关闭时调用）"""
    await OrchestratorFactory.cleanup()


def get_workflow_executor() -> WorkflowExecutor:
    """获取 WorkflowExecutor 实例（FastAPI 依赖注入使用）"""
    return OrchestratorFactory.create_workflow_executor()

