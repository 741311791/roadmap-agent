"""
SideEffectCoordinator 集成测试

验证副作用协调器的所有场景：
- 节点开始/完成/失败
- 工作流完成/失败
- Task状态更新
- WebSocket通知发送
- Redis缓存管理
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orchestrator.side_effect_coordinator import SideEffectCoordinator
from app.services.shared.notification_service import NotificationService
from app.services.shared.execution_logger import ExecutionLogger
from app.core.orchestrator.state_manager import StateManager


@pytest.fixture
def mock_notification_service():
    """Mock 通知服务"""
    service = Mock(spec=NotificationService)
    service.publish_progress = AsyncMock()
    service.publish_failed = AsyncMock()
    return service


@pytest.fixture
def mock_execution_logger():
    """Mock 执行日志服务"""
    logger = Mock(spec=ExecutionLogger)
    logger.error = AsyncMock()
    logger.flush = AsyncMock()
    return logger


@pytest.fixture
def mock_state_manager():
    """Mock 状态管理器"""
    manager = Mock(spec=StateManager)
    manager.set_live_step = AsyncMock()
    manager.clear_live_step = AsyncMock()
    return manager


@pytest.fixture
def coordinator(mock_notification_service, mock_execution_logger, mock_state_manager):
    """创建协调器实例"""
    return SideEffectCoordinator(
        notification_service=mock_notification_service,
        execution_logger=mock_execution_logger,
        state_manager=mock_state_manager,
    )


class TestNodeLifecycle:
    """测试节点生命周期"""
    
    @pytest.mark.asyncio
    async def test_on_node_start(
        self,
        coordinator,
        mock_notification_service,
        mock_state_manager,
    ):
        """测试节点开始"""
        with patch('app.core.orchestrator.side_effect_coordinator.get_celery_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value.__aenter__.return_value = mock_db
            
            await coordinator.on_node_start(
                task_id="test-task-id",
                node_name="intent_analysis",
                roadmap_id="test-roadmap",
            )
            
            # 验证副作用
            mock_state_manager.set_live_step.assert_called_once_with(
                "test-task-id",
                "intent_analysis",
            )
            mock_notification_service.publish_progress.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_node_complete(
        self,
        coordinator,
        mock_notification_service,
        mock_state_manager,
    ):
        """测试节点完成"""
        output = {"roadmap_id": "test-roadmap", "result": "success"}
        
        await coordinator.on_node_complete(
            task_id="test-task-id",
            node_name="curriculum_design",
            output=output,
            duration_ms=1500,
        )
        
        # 验证副作用
        mock_state_manager.set_live_step.assert_called_once_with(
            "test-task-id",
            "curriculum_design",
        )
        mock_notification_service.publish_progress.assert_called_once()
        args = mock_notification_service.publish_progress.call_args
        assert args.kwargs["step"] == "curriculum_design"
        assert args.kwargs["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_on_node_failed(
        self,
        coordinator,
        mock_notification_service,
        mock_execution_logger,
    ):
        """测试节点失败"""
        error = ValueError("Test error")
        
        with patch('app.core.orchestrator.side_effect_coordinator.get_celery_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value.__aenter__.return_value = mock_db
            
            await coordinator.on_node_failed(
                task_id="test-task-id",
                node_name="validation",
                error=error,
                duration_ms=2000,
            )
            
            # 验证副作用
            mock_notification_service.publish_failed.assert_called_once()
            mock_execution_logger.error.assert_called_once()


class TestWorkflowLifecycle:
    """测试工作流生命周期"""
    
    @pytest.mark.asyncio
    async def test_on_workflow_complete(
        self,
        coordinator,
        mock_state_manager,
        mock_execution_logger,
    ):
        """测试工作流完成"""
        final_state = {
            "task_id": "test-task-id",
            "roadmap_id": "test-roadmap",
            "current_step": "tutorial_generation",
        }
        
        await coordinator.on_workflow_complete(
            task_id="test-task-id",
            final_state=final_state,
        )
        
        # 验证副作用
        mock_state_manager.clear_live_step.assert_called_once_with("test-task-id")
        mock_execution_logger.flush.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_on_workflow_failed(
        self,
        coordinator,
        mock_notification_service,
        mock_state_manager,
        mock_execution_logger,
    ):
        """测试工作流失败"""
        error = RuntimeError("Workflow crashed")
        
        with patch('app.core.orchestrator.side_effect_coordinator.get_celery_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value.__aenter__.return_value = mock_db
            
            await coordinator.on_workflow_failed(
                task_id="test-task-id",
                error=error,
            )
            
            # 验证副作用
            mock_state_manager.clear_live_step.assert_called_once_with("test-task-id")
            mock_notification_service.publish_failed.assert_called_once()
            mock_execution_logger.flush.assert_called_once()


class TestFaultTolerance:
    """测试容错性"""
    
    @pytest.mark.asyncio
    async def test_notification_failure_does_not_crash(
        self,
        coordinator,
        mock_notification_service,
    ):
        """测试通知失败不影响主流程"""
        # 模拟通知发送失败
        mock_notification_service.publish_progress.side_effect = Exception("Redis down")
        
        with patch('app.core.orchestrator.side_effect_coordinator.get_celery_session') as mock_session:
            mock_db = AsyncMock(spec=AsyncSession)
            mock_session.return_value.__aenter__.return_value = mock_db
            
            # 不应该抛出异常
            await coordinator.on_node_start(
                task_id="test-task-id",
                node_name="test_node",
            )
    
    @pytest.mark.asyncio
    async def test_database_failure_does_not_crash(
        self,
        coordinator,
        mock_state_manager,
    ):
        """测试数据库更新失败不影响主流程"""
        # 模拟数据库更新失败
        with patch('app.core.orchestrator.side_effect_coordinator.get_celery_session') as mock_session:
            mock_session.return_value.__aenter__.side_effect = Exception("DB down")
            
            # 不应该抛出异常
            await coordinator.on_node_start(
                task_id="test-task-id",
                node_name="test_node",
            )

