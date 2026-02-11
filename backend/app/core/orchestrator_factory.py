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
    edit_plan_analysis_node,  # ✅ 共享的编辑计划分析节点
    # ✅ 移除：content_generation_node（改为独立的 Celery Worker）
    # ✅ 移除：validation_edit_plan_analysis_node（使用共享的edit_plan_analysis_node）
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
            # 研发环境（ENVIRONMENT=development）：max_size=5（降低以支持多 Worker 进程）
            # 生产环境（ENVIRONMENT=production）：max_size=10
            # 
            # 说明：
            # - Celery Worker 进程数量 * max_size 不能超过数据库最大连接数
            # - 例如：4 个 Worker * 5 连接 = 20 个连接（安全范围）
            langgraph_max_size = 5 if settings.ENVIRONMENT == "development" else 10
            
            cls._connection_pool = AsyncConnectionPool(
                conninfo=settings.CHECKPOINTER_DATABASE_URL,
                min_size=2,
                max_size=langgraph_max_size,
                max_idle=600,  # ✅ 延长空闲时间到 10 分钟（防止连接过早关闭）
                timeout=120,  # ✅ 延长获取连接超时到 120 秒（大任务场景）
                reconnect_timeout=0,  # 自动重连
                open=False,  # 禁用构造函数自动打开（避免 DeprecationWarning）
                kwargs={
                    "autocommit": True,  # LangGraph checkpoint 需要自动提交
                    "connect_timeout": 60,  # ✅ 延长连接建立超时到 60 秒
                    "keepalives": 1,  # 启用 TCP keepalive
                    "keepalives_idle": 20,  # ✅ 缩短到 20 秒后开始探测（更快检测断连）
                    "keepalives_interval": 5,  # ✅ 缩短探测间隔到 5 秒
                    "keepalives_count": 6,  # ✅ 增加探测次数到 6 次（总计 30 秒）
                    "options": "-c statement_timeout=180000",  # ✅ 延长 SQL 语句超时到 180 秒（3分钟）
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
                pool_max_size=langgraph_max_size,
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
            # 传入纯函数 Node（替代 Runner 类）
            intent_node=intent_analysis_node,
            curriculum_node=curriculum_design_node,
            validation_node=structure_validation_node,
            editor_node=roadmap_edit_node,
            review_node=human_review_node,
            edit_plan_node=edit_plan_analysis_node,  # ✅ 共享的编辑计划分析节点
            # ✅ 移除：content_node（改为独立的 Celery Worker）
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

