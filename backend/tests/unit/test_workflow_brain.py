"""
WorkflowBrain 单元测试

测试覆盖:
1. NodeContext 数据类
2. node_execution 上下文管理器（成功场景）
3. node_execution 上下文管理器（异常场景）
4. _before_node 方法
5. _after_node 方法
6. _on_error 方法
7. 数据保存方法（ensure_unique_roadmap_id, save_intent_analysis, save_roadmap_framework, save_content_results）
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
import time

from app.core.orchestrator.workflow_brain import WorkflowBrain, NodeContext
from app.core.orchestrator.state_manager import StateManager
from app.services.notification_service import NotificationService
from app.services.execution_logger import ExecutionLogger


@pytest.fixture
def mock_state_manager():
    """Mock StateManager"""
    manager = MagicMock(spec=StateManager)
    manager.set_live_step = MagicMock()
    manager.clear_live_step = MagicMock()
    return manager


@pytest.fixture
def mock_notification_service():
    """Mock NotificationService"""
    service = MagicMock(spec=NotificationService)
    service.publish_progress = AsyncMock()
    return service


@pytest.fixture
def mock_execution_logger():
    """Mock ExecutionLogger"""
    logger = MagicMock(spec=ExecutionLogger)
    logger.log_workflow_start = AsyncMock()
    logger.log_workflow_complete = AsyncMock()
    logger.log_error = AsyncMock()
    return logger


@pytest.fixture
def brain(mock_state_manager, mock_notification_service, mock_execution_logger):
    """创建 WorkflowBrain 实例"""
    return WorkflowBrain(
        state_manager=mock_state_manager,
        notification_service=mock_notification_service,
        execution_logger=mock_execution_logger,
    )


@pytest.fixture
def mock_state():
    """Mock RoadmapState"""
    return {
        "task_id": "test-task-123",
        "roadmap_id": "test-roadmap-456",
        "user_request": MagicMock(),
        "intent_analysis": None,
        "roadmap_framework": None,
        "validation_result": None,
        "tutorial_refs": {},
        "resource_refs": {},
        "quiz_refs": {},
        "failed_concepts": [],
        "current_step": "init",
        "modification_count": 0,
        "human_approved": False,
        "execution_history": [],
    }


class TestNodeContext:
    """测试 NodeContext 数据类"""
    
    def test_node_context_creation(self):
        """测试 NodeContext 创建"""
        ctx = NodeContext(
            node_name="test_node",
            task_id="test-task-123",
            roadmap_id="test-roadmap-456",
            start_time=time.time(),
            state_snapshot={"key": "value"},
        )
        
        assert ctx.node_name == "test_node"
        assert ctx.task_id == "test-task-123"
        assert ctx.roadmap_id == "test-roadmap-456"
        assert isinstance(ctx.start_time, float)
        assert ctx.state_snapshot == {"key": "value"}


class TestNodeExecution:
    """测试 node_execution 上下文管理器"""
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.workflow_brain.AsyncSessionLocal")
    async def test_node_execution_success(
        self,
        mock_session_class,
        brain,
        mock_state,
        mock_state_manager,
        mock_notification_service,
        mock_execution_logger,
    ):
        """测试节点执行成功场景"""
        # Mock 数据库会话
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.update_task_status = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        with patch("app.core.orchestrator.workflow_brain.RoadmapRepository", return_value=mock_repo):
            async with brain.node_execution("test_node", mock_state) as ctx:
                # 验证 before_node 被调用
                assert isinstance(ctx, NodeContext)
                assert ctx.node_name == "test_node"
                assert ctx.task_id == "test-task-123"
            
            # 验证 state_manager.set_live_step 被调用
            mock_state_manager.set_live_step.assert_called_once_with("test-task-123", "test_node")
            
            # 验证数据库更新被调用
            mock_repo.update_task_status.assert_called()
            
            # 验证日志记录被调用
            mock_execution_logger.log_workflow_start.assert_called_once()
            mock_execution_logger.log_workflow_complete.assert_called_once()
            
            # 验证通知发送被调用（两次：开始和完成）
            assert mock_notification_service.publish_progress.call_count == 2
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.workflow_brain.AsyncSessionLocal")
    async def test_node_execution_error(
        self,
        mock_session_class,
        brain,
        mock_state,
        mock_execution_logger,
    ):
        """测试节点执行异常场景"""
        # Mock 数据库会话
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.update_task_status = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        with patch("app.core.orchestrator.workflow_brain.RoadmapRepository", return_value=mock_repo):
            with pytest.raises(ValueError, match="Test error"):
                async with brain.node_execution("test_node", mock_state):
                    raise ValueError("Test error")
            
            # 验证错误日志被调用
            mock_execution_logger.log_error.assert_called_once()
            
            # 验证数据库状态更新为 failed（在 on_error 中）
            calls = mock_repo.update_task_status.call_args_list
            # 至少有一次调用包含 status="failed"
            assert any(
                call_args.kwargs.get("status") == "failed" or
                (len(call_args.args) >= 2 and call_args.args[1] == "failed")
                for call_args in calls
            ), "Expected at least one call with status='failed'"


class TestBeforeNode:
    """测试 _before_node 方法"""
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.workflow_brain.AsyncSessionLocal")
    async def test_before_node(
        self,
        mock_session_class,
        brain,
        mock_state,
        mock_state_manager,
        mock_notification_service,
        mock_execution_logger,
    ):
        """测试 before_node 功能"""
        # Mock 数据库会话
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.update_task_status = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        with patch("app.core.orchestrator.workflow_brain.RoadmapRepository", return_value=mock_repo):
            ctx = await brain._before_node("test_node", mock_state)
            
            # 验证返回的上下文
            assert isinstance(ctx, NodeContext)
            assert ctx.node_name == "test_node"
            assert ctx.task_id == "test-task-123"
            assert ctx.roadmap_id == "test-roadmap-456"
            
            # 验证 live_step 被设置
            mock_state_manager.set_live_step.assert_called_once_with("test-task-123", "test_node")
            
            # 验证数据库更新被调用
            mock_repo.update_task_status.assert_called_once_with(
                task_id="test-task-123",
                status="processing",
                current_step="test_node",
                roadmap_id="test-roadmap-456",
            )
            
            # 验证日志记录
            mock_execution_logger.log_workflow_start.assert_called_once()
            
            # 验证通知发送
            mock_notification_service.publish_progress.assert_called_once()


class TestAfterNode:
    """测试 _after_node 方法"""
    
    @pytest.mark.asyncio
    async def test_after_node(
        self,
        brain,
        mock_state,
        mock_notification_service,
        mock_execution_logger,
    ):
        """测试 after_node 功能"""
        ctx = NodeContext(
            node_name="test_node",
            task_id="test-task-123",
            roadmap_id="test-roadmap-456",
            start_time=time.time(),
            state_snapshot={},
        )
        
        await brain._after_node(ctx, mock_state)
        
        # 验证日志记录
        mock_execution_logger.log_workflow_complete.assert_called_once()
        args = mock_execution_logger.log_workflow_complete.call_args
        assert args.kwargs["task_id"] == "test-task-123"
        assert args.kwargs["step"] == "test_node"
        assert "duration_ms" in args.kwargs
        
        # 验证通知发送
        mock_notification_service.publish_progress.assert_called_once()
        args = mock_notification_service.publish_progress.call_args
        assert args.kwargs["task_id"] == "test-task-123"
        assert args.kwargs["step"] == "test_node"
        assert args.kwargs["status"] == "completed"
        
        # 验证上下文被清理
        assert brain._current_context is None


class TestOnError:
    """测试 _on_error 方法"""
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.workflow_brain.AsyncSessionLocal")
    async def test_on_error(
        self,
        mock_session_class,
        brain,
        mock_state,
        mock_notification_service,
        mock_execution_logger,
    ):
        """测试 on_error 功能"""
        # Mock 数据库会话
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.update_task_status = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        ctx = NodeContext(
            node_name="test_node",
            task_id="test-task-123",
            roadmap_id="test-roadmap-456",
            start_time=time.time(),
            state_snapshot={},
        )
        
        error = ValueError("Test error")
        
        with patch("app.core.orchestrator.workflow_brain.RoadmapRepository", return_value=mock_repo):
            await brain._on_error(ctx, mock_state, error)
            
            # 验证数据库状态更新为 failed
            mock_repo.update_task_status.assert_called_once_with(
                task_id="test-task-123",
                status="failed",
                current_step="test_node",
                error_message="Test error",
            )
            
            # 验证错误日志
            mock_execution_logger.log_error.assert_called_once()
            args = mock_execution_logger.log_error.call_args
            assert args.kwargs["task_id"] == "test-task-123"
            assert args.kwargs["step"] == "test_node"
            assert args.kwargs["error"] == error
            
            # 验证错误通知
            mock_notification_service.publish_progress.assert_called_once()
            args = mock_notification_service.publish_progress.call_args
            assert args.kwargs["status"] == "failed"
            
            # 验证上下文被清理
            assert brain._current_context is None


class TestDataSavingMethods:
    """测试数据保存方法"""
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.workflow_brain.AsyncSessionLocal")
    @patch("app.core.orchestrator.workflow_brain.ensure_unique_roadmap_id")
    async def test_ensure_unique_roadmap_id(
        self,
        mock_ensure_unique,
        mock_session_class,
        brain,
    ):
        """测试 ensure_unique_roadmap_id"""
        # Mock
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        mock_repo = MagicMock()
        mock_ensure_unique.return_value = "unique-roadmap-id"
        
        with patch("app.core.orchestrator.workflow_brain.RoadmapRepository", return_value=mock_repo):
            result = await brain.ensure_unique_roadmap_id("test-roadmap-id")
            
            assert result == "unique-roadmap-id"
            mock_ensure_unique.assert_called_once_with("test-roadmap-id", mock_repo)
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.workflow_brain.AsyncSessionLocal")
    async def test_save_intent_analysis(
        self,
        mock_session_class,
        brain,
    ):
        """测试 save_intent_analysis"""
        # Mock
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.save_intent_analysis_metadata = AsyncMock()
        mock_repo.update_task_status = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        mock_intent_analysis = MagicMock()
        
        with patch("app.core.orchestrator.workflow_brain.RoadmapRepository", return_value=mock_repo):
            await brain.save_intent_analysis(
                task_id="test-task-123",
                intent_analysis=mock_intent_analysis,
                unique_roadmap_id="unique-roadmap-id",
            )
            
            # 验证 save_intent_analysis_metadata 被调用
            mock_repo.save_intent_analysis_metadata.assert_called_once_with(
                "test-task-123",
                mock_intent_analysis,
            )
            
            # 验证 update_task_status 被调用
            mock_repo.update_task_status.assert_called_once()
            
            # 验证 commit 被调用
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.workflow_brain.AsyncSessionLocal")
    async def test_save_roadmap_framework(
        self,
        mock_session_class,
        brain,
    ):
        """测试 save_roadmap_framework"""
        # Mock
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.save_roadmap_metadata = AsyncMock()
        mock_repo.update_task_status = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        mock_framework = MagicMock()
        mock_framework.stages = []
        
        with patch("app.core.orchestrator.workflow_brain.RoadmapRepository", return_value=mock_repo):
            await brain.save_roadmap_framework(
                task_id="test-task-123",
                roadmap_id="test-roadmap-456",
                user_id="test-user-789",
                framework=mock_framework,
            )
            
            # 验证 save_roadmap_metadata 被调用
            mock_repo.save_roadmap_metadata.assert_called_once_with(
                "test-roadmap-456",
                "test-user-789",
                mock_framework,
            )
            
            # 验证 commit 被调用
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.workflow_brain.AsyncSessionLocal")
    async def test_save_content_results(
        self,
        mock_session_class,
        brain,
    ):
        """测试 save_content_results"""
        # Mock
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.save_tutorials_batch = AsyncMock()
        mock_repo.save_resources_batch = AsyncMock()
        mock_repo.save_quizzes_batch = AsyncMock()
        mock_repo.update_task_status = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        tutorial_refs = {"concept1": MagicMock()}
        resource_refs = {"concept1": MagicMock()}
        quiz_refs = {"concept1": MagicMock()}
        failed_concepts = []
        
        with patch("app.core.orchestrator.workflow_brain.RoadmapRepository", return_value=mock_repo):
            await brain.save_content_results(
                task_id="test-task-123",
                roadmap_id="test-roadmap-456",
                tutorial_refs=tutorial_refs,
                resource_refs=resource_refs,
                quiz_refs=quiz_refs,
                failed_concepts=failed_concepts,
            )
            
            # 验证批量保存被调用
            mock_repo.save_tutorials_batch.assert_called_once_with(tutorial_refs, "test-roadmap-456")
            mock_repo.save_resources_batch.assert_called_once_with(resource_refs, "test-roadmap-456")
            mock_repo.save_quizzes_batch.assert_called_once_with(quiz_refs, "test-roadmap-456")
            
            # 验证最终状态更新
            mock_repo.update_task_status.assert_called_once()
            call_args = mock_repo.update_task_status.call_args
            assert call_args.kwargs["status"] == "completed"  # 无失败概念
            
            # 验证 commit 被调用
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    @patch("app.core.orchestrator.workflow_brain.AsyncSessionLocal")
    async def test_save_content_results_with_failures(
        self,
        mock_session_class,
        brain,
    ):
        """测试 save_content_results（包含失败概念）"""
        # Mock
        mock_session = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.save_tutorials_batch = AsyncMock()
        mock_repo.update_task_status = AsyncMock()
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = None
        mock_session_class.return_value = mock_session
        
        tutorial_refs = {"concept1": MagicMock()}
        failed_concepts = ["concept2", "concept3"]
        
        with patch("app.core.orchestrator.workflow_brain.RoadmapRepository", return_value=mock_repo):
            await brain.save_content_results(
                task_id="test-task-123",
                roadmap_id="test-roadmap-456",
                tutorial_refs=tutorial_refs,
                resource_refs={},
                quiz_refs={},
                failed_concepts=failed_concepts,
            )
            
            # 验证最终状态为 partial_failure
            call_args = mock_repo.update_task_status.call_args
            assert call_args.kwargs["status"] == "partial_failure"
            assert call_args.kwargs["failed_concepts"] is not None

