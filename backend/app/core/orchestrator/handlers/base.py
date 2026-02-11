"""
Handler基类（重构版 - 单一职责 + 强类型）

定义所有Node输出处理器的统一接口

重构改进：
- Handler只负责保存业务数据到数据库
- 所有副作用（状态更新、通知、缓存）由SideEffectCoordinator统一管理
- 简化Handler职责，提高可测试性
- 支持泛型和强类型输入验证
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, TypeVar, Generic, Type
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from app.core.orchestrator.state_manager import StateManager

logger = structlog.get_logger()

# 泛型类型变量
InputT = TypeVar("InputT", bound=BaseModel)


class NodeOutputHandler(ABC, Generic[InputT]):
    """
    节点输出处理器基类（重构版 - 强类型）
    
    职责（单一职责）：
    1. 将 dict 转换为强类型 Pydantic Model
    2. 保存节点输出到数据库（业务数据持久化）
    3. 更新 live_step 缓存（实时进度查询）
    
    不再负责：
    - ❌ Task 状态更新（由 SideEffectCoordinator 管理）
    - ❌ WebSocket 通知发送（由 SideEffectCoordinator 管理）
    - ❌ 执行日志记录（由 Node 内部记录或 Coordinator 统一记录）
    
    设计原则：
    - 每个节点有对应的Handler
    - Handler只保存业务数据，不处理副作用
    - 副作用由Executor中的SideEffectCoordinator统一处理
    - 子类必须定义 input_model_class 属性指定输入类型
    """
    
    # 子类必须定义此属性
    input_model_class: Type[InputT]
    
    def __init__(
        self,
        state_manager: "StateManager",
    ):
        """
        初始化Handler
        
        Args:
            state_manager: 状态管理器（用于更新live_step缓存）
        """
        self.state_manager = state_manager
    
    async def handle(
        self,
        output: dict,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        处理节点输出（核心方法 - 模板方法模式 + 自动类型转换）
        
        执行顺序：
        1. 将 dict 转换为强类型 Pydantic Model
        2. 调用子类的 _handle_output() 保存业务数据
        3. 更新 live_step 缓存（Redis）- 提供实时进度
        
        Args:
            output: 节点输出数据（dict）
            task_id: 任务ID
            session: 数据库会话（已开启事务）
        
        Raises:
            ValueError: Handler 输入验证失败
            Exception: 处理失败时抛出异常
        """
        # 1. 自动将 dict 转换为强类型 Pydantic Model
        try:
            # 🔍 调试日志：查看实际收到的数据结构
            logger.info(
                "handler_input_debug",
                task_id=task_id,
                handler_class=self.__class__.__name__,
                output_type=type(output).__name__,
                output_keys=list(output.keys()) if isinstance(output, dict) else "not_dict",
                output_sample=str(output)[:300],  # 查看前300字符
            )
            
            typed_input = self.input_model_class.model_validate(output)
        except ValidationError as e:
            logger.error(
                "handler_input_validation_failed",
                task_id=task_id,
                handler_class=self.__class__.__name__,
                validation_errors=e.errors(),
                output_sample=str(output)[:500],  # 添加实际数据样本
                exc_info=True,
            )
            raise ValueError(
                f"Handler 输入验证失败: {e}"
            ) from e
        
        # 2. 调用子类实现保存业务数据
        await self._handle_output(typed_input, task_id, session)
        
        # 3. 更新 live_step 缓存（提供实时进度）
        node_name = self.get_node_name()
        await self.state_manager.set_live_step(task_id, node_name)
        
        logger.debug(
            "handler_live_step_updated",
            task_id=task_id,
            node_name=node_name,
        )
    
    @abstractmethod
    async def _handle_output(
        self,
        output: InputT,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        处理节点输出的具体实现（子类必须实现）
        
        只负责保存业务数据到数据库，不处理缓存和通知。
        
        Args:
            output: 节点输出数据（强类型 Pydantic Model）
            task_id: 任务ID
            session: 数据库会话
        """
        pass
    
    
    @abstractmethod
    def get_node_name(self) -> str:
        """
        获取节点名称（必须实现）
        
        Returns:
            节点名称（如 "intent_analysis"）
        """
        pass

