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
from app.services.shared.notification_service import notification_service
from app.services.shared.execution_logger import execution_logger
from .orchestrator.base import WorkflowConfig
from .orchestrator.state_manager import StateManager
from .orchestrator.routers import WorkflowRouter
from .orchestrator.builder import WorkflowBuilder
from .orchestrator.executor import WorkflowExecutor
from .orchestrator.runtime_context import RuntimeContext
from .orchestrator.handlers import (
    HandlerRegistry,
    IntentAnalysisHandler,
    CurriculumDesignHandler,
    ValidationHandler,
    EditorHandler,
    ReviewHandler,
    ContentHandler,
    EditPlanHandler,
    # ✅ 移除：ValidationEditPlanHandler（使用共享的EditPlanHandler）
)
from .orchestrator.nodes import (
    intent_analysis_node,
    curriculum_design_node,
    structure_validation_node,
    roadmap_edit_node,
    human_review_node,
    edit_plan_analysis_node,
    auto_content_generation_node,
)

logger = structlog.get_logger()


class OrchestratorFactory:
    """
    工作流编排器工厂
    
    使用单例模式管理共享组件（StateManager, Checkpointer）
    使用连接池来管理数据库连接，防止长时间运行时连接超时。
    
    Fork 安全性保证：
    - 使用进程 ID 检测跨进程共享
    - 子进程自动重新初始化连接池
    - 避免跨进程使用失效的连接
    """
    
    _state_manager: StateManager | None = None
    _checkpointer: AsyncPostgresSaver | None = None
    _connection_pool: AsyncConnectionPool | None = None
    _agent_factory: AgentFactory | None = None
    _initialized: bool = False
    _process_id: int | None = None  # ✅ 新增：跟踪初始化时的进程 ID
    
    @classmethod
    def get_agent_factory(cls) -> AgentFactory:
        """获取 AgentFactory 单例"""
        if not cls._initialized:
            raise RuntimeError("OrchestratorFactory 未初始化，请先调用 initialize()")
        return cls._agent_factory
    
    @classmethod
    def get_state_manager(cls) -> StateManager:
        """获取 StateManager 单例"""
        if not cls._initialized:
            raise RuntimeError("OrchestratorFactory 未初始化，请先调用 initialize()")
        return cls._state_manager
    
    @classmethod
    async def initialize(cls) -> None:
        """
        初始化工厂（应用启动时调用一次）
        
        创建 Checkpointer 和 StateManager 单例。
        使用连接池来管理连接生命周期，防止长时间运行时连接超时。
        
        Fork 安全性：
        - 检测进程 ID 变化（Celery Worker fork 后）
        - 如果进程 ID 改变，强制重新初始化
        - 确保每个进程使用独立的连接池
        """
        import os
        current_pid = os.getpid()
        
        # ✅ Fork 安全性检查 1：如果进程 ID 改变，说明发生了 fork
        if cls._process_id is not None and cls._process_id != current_pid:
            logger.warning(
                "orchestrator_factory_fork_detected",
                parent_pid=cls._process_id,
                child_pid=current_pid,
                message="检测到进程 fork，强制重新初始化连接池",
            )
            
            # 清理父进程的资源引用（避免跨进程使用）
            # 注意：不能调用 close()，因为父进程可能仍在使用连接池
            cls._state_manager = None
            cls._checkpointer = None
            cls._connection_pool = None
            cls._agent_factory = None
            cls._initialized = False
            cls._process_id = None
        
        # ✅ Fork 安全性检查 2：如果已初始化且在同一进程，直接返回
        if cls._initialized and cls._process_id == current_pid:
            logger.info(
                "orchestrator_factory_already_initialized",
                process_id=current_pid,
            )
            return
        
        # 创建 StateManager 单例
        cls._state_manager = StateManager()
        
        # 创建 AgentFactory 单例
        cls._agent_factory = AgentFactory(settings)
        
        # 创建 AsyncPostgresSaver（使用连接池，阿里云 RDS 长链路网络优化）
        try:
            # 连接池参数说明：
            # - min_size=1: 最小保持 1 个连接，避免完全冷启动
            # - max_size: 4C8G 单机生产默认收敛到 3，避免 API 和多个 Worker 空闲时也常驻大量连接
            # - max_idle=60: 空闲连接最多保持 60 秒即主动关闭，防止被阿里云代理层单方面关闭
            # - max_lifetime=300: 连接最长存活 5 分钟，定期替换（防止跨越阿里云 RDS Proxy 超时）
            # - check=AsyncConnectionPool.check_connection: 借出连接前先 ping，快速淘汰坏连接
            #   （这是修复 "consuming input failed: Operation timed out" 的核心手段）
            # - timeout=120: 获取连接超时 120 秒（大任务场景）
            # - reconnect_timeout=0: 重连失败无限重试
            # 
            # 连接参数（kwargs）：
            # - autocommit=True: LangGraph checkpoint 需要自动提交模式
            # - connect_timeout=15: 阿里云 RDS 建连超时 15 秒（实测约 5s，15s 留足余量）
            # - keepalives=1: 启用 TCP keepalive
            # - keepalives_idle=10: 空闲 10 秒后开始发送探测（比阿里云代理层 idle timeout 更激进）
            # - keepalives_interval=5: 探测间隔 5 秒
            # - keepalives_count=3: 最多 3 次探测失败后客户端主动断开（总计 10+15=25 秒内判定死连接）
            # - options="-c statement_timeout=120000": SQL 语句超时 120 秒
            
            cls._connection_pool = AsyncConnectionPool(
                conninfo=settings.CHECKPOINTER_DATABASE_URL,
                min_size=settings.LANGGRAPH_CHECKPOINTER_POOL_MIN_SIZE,
                max_size=settings.LANGGRAPH_CHECKPOINTER_POOL_MAX_SIZE,
                max_idle=60,       # 主动在 60s 内关闭空闲连接，早于阿里云代理层超时
                max_lifetime=300,  # 连接最长存活 5 分钟，定期轮换防止跨越代理层 TCP 状态超时
                check=AsyncConnectionPool.check_connection,  # 借出前 ping，快速淘汰坏连接
                timeout=120,
                reconnect_timeout=0,
                open=False,
                kwargs={
                    "autocommit": True,
                    "connect_timeout": 15,
                    "keepalives": 1,
                    "keepalives_idle": 10,   # 比阿里云代理层更激进的 keepalive
                    "keepalives_interval": 5,
                    "keepalives_count": 3,   # 25 秒内判定死连接并主动断开
                    "options": "-c statement_timeout=120000",
                },
            )
            
            logger.info(
                "langgraph_connection_pool_configured",
                environment=settings.ENVIRONMENT,
                min_size=settings.LANGGRAPH_CHECKPOINTER_POOL_MIN_SIZE,
                max_size=settings.LANGGRAPH_CHECKPOINTER_POOL_MAX_SIZE,
            )
            
            # 打开连接池
            await cls._connection_pool.open()
            
            # 使用连接池创建 AsyncPostgresSaver
            cls._checkpointer = AsyncPostgresSaver(cls._connection_pool)
            
            # 初始化 checkpointer 表结构
            # UniqueViolation 表示迁移记录已存在（重新部署场景），属于正常幂等行为，直接跳过
            try:
                await cls._checkpointer.setup()
            except Exception as setup_err:
                from psycopg.errors import UniqueViolation
                if isinstance(setup_err, UniqueViolation):
                    logger.info(
                        "checkpointer_setup_skipped",
                        reason="checkpoint_migrations 已存在，跳过重复迁移",
                    )
                else:
                    raise
            
            logger.info(
                "orchestrator_factory_initialized",
                checkpointer_type="AsyncPostgresSaver",
                pool_min_size=settings.LANGGRAPH_CHECKPOINTER_POOL_MIN_SIZE,
                pool_max_size=settings.LANGGRAPH_CHECKPOINTER_POOL_MAX_SIZE,
                process_id=current_pid,  # ✅ 记录进程 ID
                database_url=settings.CHECKPOINTER_DATABASE_URL.split("@")[-1].split("?")[0],  # 隐藏凭据和参数
            )
            
            cls._initialized = True
            cls._process_id = current_pid  # ✅ 保存当前进程 ID
            
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
        cls._process_id = None  # ✅ 重置进程 ID
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
    def get_parent_checkpointer(cls) -> AsyncPostgresSaver:
        """
        获取父图 Checkpointer（命名空间隔离）
        
        使用命名空间 'parent_graph' 隔离父图的 checkpoint 数据。
        这样主图和子图可以共享 thread_id，但状态完全独立。
        
        Returns:
            父图专用的 Checkpointer（命名空间：parent_graph）
        
        注意：
            AsyncPostgresSaver 不支持 with_namespace 方法。
            当前直接返回主 checkpointer，通过 thread_id 命名约定来区分不同图。
        """
        if not cls._initialized:
            raise RuntimeError("OrchestratorFactory 未初始化，请先调用 initialize()")
        
        return cls._checkpointer
    
    @classmethod
    def get_child_checkpointer(cls) -> AsyncPostgresSaver:
        """
        获取子图 Checkpointer（命名空间隔离）
        
        使用命名空间 'child_graph' 隔离子图的 checkpoint 数据。
        子图可以记录并发执行的详细进度（如哪些 Concept 已完成）。
        
        Returns:
            子图专用的 Checkpointer（命名空间：child_graph）
        
        注意：
            AsyncPostgresSaver 不支持 with_namespace 方法。
            当前暂时返回主 checkpointer，通过 thread_id 命名约定来区分。
            主图 thread_id: {task_id}
            子图 thread_id: {task_id}:child:{concept_id}
        """
        if not cls._initialized:
            raise RuntimeError("OrchestratorFactory 未初始化，请先调用 initialize()")
        
        return cls._checkpointer
    
    @classmethod
    def create_workflow_executor(cls) -> WorkflowExecutor:
        """
        创建 WorkflowExecutor 实例（重构版 - Handler模式）
        
        每次调用都创建新实例，但共享 StateManager 和 Checkpointer。
        
        重构改进：
        - 移除 WorkflowBrain，使用 RuntimeContext 和 HandlerRegistry
        - 使用纯函数 Node 替代 Runner 类
        - 在 Stream Loop 中统一处理副作用
        
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
        
        # ===== 核心重构：创建 RuntimeContext 替代 WorkflowBrain =====
        # ✅ 双 Checkpointer 架构：传入子图专用的 checkpointer
        runtime_context = RuntimeContext(
            agent_factory=agent_factory,
            notification_service=notification_service,
            execution_logger=execution_logger,
            state_manager=state_manager,
            child_checkpointer=cls.get_child_checkpointer(),  # 新增：子图专用 checkpointer
        )
        
        # ===== 核心重构：创建 HandlerRegistry 并注册所有 Handler =====
        handler_registry = HandlerRegistry()
        
        # 注册所有 Handler（重构版 - 只传入 state_manager）
        handler_registry.register(
            "intent_analysis",
            IntentAnalysisHandler(state_manager),
        )
        handler_registry.register(
            "curriculum_design",
            CurriculumDesignHandler(state_manager),
        )
        handler_registry.register(
            "structure_validation",
            ValidationHandler(state_manager),
        )
        handler_registry.register(
            "roadmap_edit",
            EditorHandler(state_manager),
        )
        handler_registry.register(
            "human_review",
            ReviewHandler(state_manager),
        )
        handler_registry.register(
            "content_generation",
            ContentHandler(state_manager),
        )
        # ✅ 共享的编辑计划分析Handler（validation和review都使用此Handler）
        handler_registry.register(
            "edit_plan_analysis",
            EditPlanHandler(state_manager),
        )
        
        logger.info(
            "handler_registry_created",
            registered_nodes=handler_registry.get_registered_nodes(),
        )
        
        # ===== 创建副作用协调器 =====
        from app.core.orchestrator.side_effect_coordinator import SideEffectCoordinator
        
        side_effect_coordinator = SideEffectCoordinator(
            notification_service=notification_service,
            execution_logger=execution_logger,
            state_manager=state_manager,
        )
        
        logger.info("side_effect_coordinator_created")
        
        # ===== 核心重构：创建 Builder（使用纯函数 Node）=====
        builder = WorkflowBuilder(
            config=config,
            router=router,
            intent_node=intent_analysis_node,
            curriculum_node=curriculum_design_node,
            validation_node=structure_validation_node,
            editor_node=roadmap_edit_node,
            review_node=human_review_node,
            edit_plan_node=edit_plan_analysis_node,
            auto_content_node=auto_content_generation_node,
        )
        
        # ===== 创建 Executor（传入所有依赖）=====
        # ✅ 双 Checkpointer 架构：使用父图专用的 checkpointer
        executor = WorkflowExecutor(
            builder=builder,
            state_manager=state_manager,
            checkpointer=cls.get_parent_checkpointer(),  # 使用父图专用 checkpointer
            execution_logger=execution_logger,
            runtime_context=runtime_context,
            handler_registry=handler_registry,
            side_effect_coordinator=side_effect_coordinator,
        )
        
        logger.info(
            "workflow_executor_created",
            architecture="handler_pattern",
            nodes_count=9,  # 包含新增的 workflow_verification 节点
            handlers_count=len(handler_registry.get_registered_nodes()),
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

