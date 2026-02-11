"""
运行时上下文

通过RunnableConfig传递依赖到Node函数，避免在State中传递不可序列化的对象
"""
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict
import structlog

from app.agents.factory import AgentFactory
from app.services.shared.notification_service import NotificationService
from app.services.shared.execution_logger import ExecutionLogger
from app.core.orchestrator.state_manager import StateManager
from app.models.domain import UserConstraints, IntentAnalysisOutput

if TYPE_CHECKING:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = structlog.get_logger()


@dataclass
class RuntimeContext:
    """
    运行时上下文 - 通过RunnableConfig传递
    
    包含Node执行所需的所有依赖，但不包含不可序列化的对象（如AsyncSession）
    
    设计原则：
    1. 只包含无状态的服务实例
    2. 不包含数据库连接等有状态对象
    3. 通过config["configurable"]["runtime_context"]传递给Node
    
    双 Checkpointer 架构：
    - parent_checkpointer: 主图使用（记录主图节点进度）
    - child_checkpointer: 子图使用（记录子图并发任务进度）
    - 两者共享 thread_id，但状态完全隔离
    
    使用示例：
        # 在WorkflowExecutor中创建
        context = RuntimeContext(
            agent_factory=agent_factory,
            notification_service=notification_service,
            execution_logger=execution_logger,
            state_manager=state_manager,
            child_checkpointer=child_checkpointer,
        )
        
        # 在Node函数中使用
        async def my_node(state: RoadmapState, config: RunnableConfig):
            ctx = config["configurable"]["runtime_context"]
            agent = ctx.agent_factory.create_my_agent()
            
            # 如果需要调用子图
            subgraph = build_subgraph(checkpointer=ctx.child_checkpointer)
            result = await subgraph.ainvoke(state, config)
            ...
    """
    
    # Agent工厂（用于创建各类Agent实例）
    agent_factory: AgentFactory
    
    # 通知服务（用于发送WebSocket消息）
    notification_service: NotificationService
    
    # 执行日志服务（用于记录结构化日志）
    execution_logger: ExecutionLogger
    
    # 状态管理器（用于管理live_step缓存）
    state_manager: StateManager
    
    # 子图专用 Checkpointer（双 Checkpointer 架构）
    child_checkpointer: "AsyncPostgresSaver"
    
    # 约束缓存（避免重复查询数据库）
    _constraints_cache: Dict[str, UserConstraints] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后的验证"""
        logger.info(
            "runtime_context_created",
            has_agent_factory=self.agent_factory is not None,
            has_notification_service=self.notification_service is not None,
            has_execution_logger=self.execution_logger is not None,
            has_state_manager=self.state_manager is not None,
            has_child_checkpointer=self.child_checkpointer is not None,
            dual_checkpointer_enabled=True,
        )
    
    def create_agent(self, agent_type: str):
        """
        便捷方法：根据类型创建Agent
        
        Args:
            agent_type: Agent类型（如 "intent_analyzer"）
        
        Returns:
            Agent实例
        
        Raises:
            AttributeError: 如果Agent类型不存在
        """
        factory_method = getattr(self.agent_factory, f"create_{agent_type}")
        return factory_method()
    
    def cache_user_constraints(self, roadmap_id: str, constraints: UserConstraints) -> None:
        """
        缓存用户约束
        
        Args:
            roadmap_id: 路线图ID
            constraints: 约束字典
        """
        self._constraints_cache[roadmap_id] = constraints
        logger.debug(
            "user_constraints_cached",
            roadmap_id=roadmap_id,
            constraints_count=len(constraints),
        )
    
    def get_cached_constraints(self, roadmap_id: str) -> UserConstraints | None:
        """
        从缓存获取用户约束
        
        Args:
            roadmap_id: 路线图ID
            
        Returns:
            约束字典，如果缓存中不存在则返回 None
        """
        constraints = self._constraints_cache.get(roadmap_id)
        if constraints:
            logger.debug(
                "user_constraints_cache_hit",
                roadmap_id=roadmap_id,
                constraints_count=len(constraints),
            )
        return constraints
    
    async def get_user_constraints(
        self,
        roadmap_id: str,
        intent_analysis: IntentAnalysisOutput | None = None
    ) -> UserConstraints:
        """
        获取用户约束（带缓存）
        
        优先级：
        1. 从缓存获取
        2. 从 intent_analysis 提取
        3. 从数据库查询
        4. 返回空字典
        
        Args:
            roadmap_id: 路线图ID
            intent_analysis: 意图分析结果（可选）
            
        Returns:
            约束字典
        """
        # 优先级1：从缓存获取
        cached = self.get_cached_constraints(roadmap_id)
        if cached:
            return cached
        
        # 优先级2：从 intent_analysis 提取
        if intent_analysis and intent_analysis.full_analysis_data:
            constraints = intent_analysis.full_analysis_data
            self.cache_user_constraints(roadmap_id, constraints)
            return constraints
        
        # 优先级3：从数据库查询
        try:
            from app.crud.crud_intent_analysis import get_intent_analysis_crud
            from app.db.session import async_session_maker
            
            async with async_session_maker() as session:
                intent_crud = get_intent_analysis_crud()
                metadata = await intent_crud.get_by_roadmap_id(session, roadmap_id)
                
                if metadata and metadata.full_analysis_data:
                    constraints = metadata.full_analysis_data
                    self.cache_user_constraints(roadmap_id, constraints)
                    return constraints
        except Exception as e:
            logger.warning(
                "failed_to_load_user_constraints_from_db",
                roadmap_id=roadmap_id,
                error=str(e)
            )
        
        # 优先级4：返回空字典
        logger.warning(
            "user_constraints_not_found",
            roadmap_id=roadmap_id,
        )
        return {}

