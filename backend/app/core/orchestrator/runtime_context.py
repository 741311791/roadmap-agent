"""
运行时上下文

通过RunnableConfig传递依赖到Node函数，避免在State中传递不可序列化的对象
"""
from dataclasses import dataclass
import structlog

from app.agents.factory import AgentFactory
from app.services.shared.notification_service import NotificationService
from app.services.shared.execution_logger import ExecutionLogger
from app.core.orchestrator.state_manager import StateManager

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
    
    使用示例：
        # 在WorkflowExecutor中创建
        context = RuntimeContext(
            agent_factory=agent_factory,
            notification_service=notification_service,
            execution_logger=execution_logger,
            state_manager=state_manager,
        )
        
        # 在Node函数中使用
        async def my_node(state: RoadmapState, config: RunnableConfig):
            ctx = config["configurable"]["runtime_context"]
            agent = ctx.agent_factory.create_my_agent()
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
    
    def __post_init__(self):
        """初始化后的验证"""
        logger.info(
            "runtime_context_created",
            has_agent_factory=self.agent_factory is not None,
            has_notification_service=self.notification_service is not None,
            has_execution_logger=self.execution_logger is not None,
            has_state_manager=self.state_manager is not None,
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

