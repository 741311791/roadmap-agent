"""
Handler注册表（重构版 - 简化职责）

管理所有Node的Handler实例，提供统一的分发接口

重构改进：
- 移除 on_start、on_complete、on_error 方法
- Handler只负责保存业务数据
- 副作用由 SideEffectCoordinator 统一管理
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import NodeOutputHandler

logger = structlog.get_logger()


class HandlerRegistry:
    """
    Handler注册表（重构版）
    
    职责（简化）：
    1. 注册所有节点的Handler
    2. 根据节点名称分发业务数据保存逻辑
    
    不再负责：
    - ❌ 副作用协调（由 SideEffectCoordinator 管理）
    - ❌ on_start/on_complete/on_error 调用
    
    使用示例：
        registry = HandlerRegistry()
        registry.register("intent_analysis", IntentAnalysisHandler(...))
        
        # 在Stream Loop中调用
        await registry.handle("intent_analysis", output, task_id, session)
    """
    
    def __init__(self):
        """初始化注册表"""
        self._handlers: dict[str, NodeOutputHandler] = {}
        logger.info("handler_registry_initialized")
    
    def register(self, node_name: str, handler: NodeOutputHandler) -> None:
        """
        注册Handler
        
        Args:
            node_name: 节点名称（如 "intent_analysis"）
            handler: Handler实例
        
        Raises:
            ValueError: 如果节点名称已注册
        """
        if node_name in self._handlers:
            raise ValueError(f"Handler for node '{node_name}' already registered")
        
        self._handlers[node_name] = handler
        
        logger.info(
            "handler_registered",
            node_name=node_name,
            handler_class=handler.__class__.__name__,
        )
    
    async def handle(
        self,
        node_name: str,
        output: dict,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        分发处理逻辑
        
        Args:
            node_name: 节点名称
            output: 节点输出
            task_id: 任务ID
            session: 数据库会话（已开启事务）
        
        Raises:
            KeyError: 如果节点名称未注册
        """
        handler = self._handlers.get(node_name)
        
        if not handler:
            logger.warning(
                "handler_not_found",
                node_name=node_name,
                task_id=task_id,
                message="节点未注册Handler，跳过副作用处理",
            )
            return
        
        logger.debug(
            "handler_dispatching",
            node_name=node_name,
            task_id=task_id,
            handler_class=handler.__class__.__name__,
        )
        
        # 调用Handler处理（只保存业务数据）
        await handler.handle(output, task_id, session)
    
    def get_registered_nodes(self) -> list[str]:
        """
        获取所有已注册的节点名称
        
        Returns:
            节点名称列表
        """
        return list(self._handlers.keys())
    
    def has_handler(self, node_name: str) -> bool:
        """
        检查节点是否已注册Handler
        
        Args:
            node_name: 节点名称
        
        Returns:
            是否已注册
        """
        return node_name in self._handlers

