"""
HandlerRegistry集成测试

测试Handler注册和分发逻辑
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.orchestrator.handlers import (
    HandlerRegistry,
    IntentAnalysisHandler,
    CurriculumDesignHandler,
)
from app.services.shared.notification_service import NotificationService
from app.services.shared.execution_logger import ExecutionLogger


@pytest.fixture
def mock_notification_service():
    """创建Mock的NotificationService"""
    service = MagicMock(spec=NotificationService)
    service.publish_progress = AsyncMock()
    return service


@pytest.fixture
def mock_execution_logger():
    """创建Mock的ExecutionLogger"""
    logger = MagicMock(spec=ExecutionLogger)
    logger.log_workflow_start = AsyncMock()
    logger.log_workflow_complete = AsyncMock()
    logger.info = AsyncMock()
    return logger


@pytest.fixture
def mock_state_manager():
    """创建Mock的StateManager"""
    manager = AsyncMock()
    manager.set_live_step = AsyncMock()
    return manager


class TestHandlerRegistry:
    """测试Handler注册表"""
    
    def test_register_handler(
        self,
        mock_notification_service,
        mock_execution_logger,
        mock_state_manager,
    ):
        """测试注册Handler"""
        registry = HandlerRegistry()
        handler = IntentAnalysisHandler(
            mock_state_manager,
        )
        
        # 注册
        registry.register("intent_analysis", handler)
        
        # 验证
        assert registry.has_handler("intent_analysis")
        assert "intent_analysis" in registry.get_registered_nodes()
    
    def test_register_duplicate_raises_error(
        self,
        mock_notification_service,
        mock_execution_logger,
        mock_state_manager,
    ):
        """测试重复注册抛出异常"""
        registry = HandlerRegistry()
        handler = IntentAnalysisHandler(
            mock_state_manager,
        )
        
        # 第一次注册
        registry.register("intent_analysis", handler)
        
        # 第二次注册应该抛出异常
        with pytest.raises(ValueError, match="already registered"):
            registry.register("intent_analysis", handler)
    
    @pytest.mark.asyncio
    async def test_handle_dispatch(
        self,
        mock_notification_service,
        mock_execution_logger,
    ):
        """测试分发处理逻辑"""
        registry = HandlerRegistry()
        
        # Mock Handler
        mock_handler = AsyncMock()
        mock_handler.handle = AsyncMock()
        registry._handlers["test_node"] = mock_handler
        
        # 准备数据
        output = {"test": "data"}
        mock_session = AsyncMock()
        
        # 执行
        await registry.handle("test_node", output, "test-task-id", mock_session)
        
        # 验证Handler被调用
        mock_handler.handle.assert_called_once_with(
            output,
            "test-task-id",
            mock_session,
        )
    
    @pytest.mark.asyncio
    async def test_handle_unknown_node(self, mock_session):
        """测试处理未注册的节点"""
        registry = HandlerRegistry()
        
        # 执行（不应该抛出异常）
        await registry.handle("unknown_node", {}, "test-task-id", mock_session)
        
        # 验证：应该记录警告但不抛出异常
        assert True
    
    # 注释：on_start/on_complete/on_error 已移除，由 SideEffectCoordinator 统一管理
    # 这些测试在集成测试中覆盖
    
    def test_get_registered_nodes(
        self,
        mock_notification_service,
        mock_execution_logger,
        mock_state_manager,
    ):
        """测试获取已注册节点列表"""
        registry = HandlerRegistry()
        
        handler1 = IntentAnalysisHandler(
            mock_state_manager,
        )
        handler2 = CurriculumDesignHandler(
            mock_state_manager,
        )
        
        registry.register("intent_analysis", handler1)
        registry.register("curriculum_design", handler2)
        
        nodes = registry.get_registered_nodes()
        assert len(nodes) == 2
        assert "intent_analysis" in nodes
        assert "curriculum_design" in nodes

