"""
Handler集成测试

测试Handler的副作用处理逻辑（数据库保存、日志、通知）
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.orchestrator.handlers import (
    IntentAnalysisHandler,
    CurriculumDesignHandler,
    ValidationHandler,
    ContentHandler,
)
from app.services.shared.notification_service import NotificationService
from app.services.shared.execution_logger import ExecutionLogger
from app.models.domain import (
    IntentAnalysisOutput,
    RoadmapFramework,
    ValidationOutput,
    ValidationIssue,
    DimensionScore,
)


@pytest.fixture
def mock_notification_service():
    """创建Mock的NotificationService"""
    service = MagicMock(spec=NotificationService)
    service.publish_progress = AsyncMock()
    service.publish_human_review_required = AsyncMock()
    service.publish_completed = AsyncMock()
    service.publish_failed = AsyncMock()
    service.publish_concept_complete = AsyncMock()
    service.publish_concept_failed = AsyncMock()
    return service


@pytest.fixture
def mock_execution_logger():
    """创建Mock的ExecutionLogger"""
    logger = MagicMock(spec=ExecutionLogger)
    logger.log_workflow_start = AsyncMock()
    logger.log_workflow_complete = AsyncMock()
    logger.error = AsyncMock()
    logger.info = AsyncMock()
    return logger


@pytest.fixture
def mock_state_manager():
    """创建Mock的StateManager"""
    manager = AsyncMock()
    manager.set_live_step = AsyncMock()
    manager.clear_live_step = AsyncMock()
    return manager


@pytest.fixture
def mock_session():
    """创建Mock的AsyncSession"""
    session = AsyncMock(spec=AsyncSession)
    return session


class TestIntentAnalysisHandler:
    """测试意图分析Handler"""
    
    @pytest.mark.asyncio
    async def test_handle_intent_analysis(
        self,
        mock_notification_service,
        mock_execution_logger,
        mock_state_manager,
        mock_session,
    ):
        """测试处理意图分析输出"""
        # 创建Handler
        handler = IntentAnalysisHandler(
            mock_state_manager,
        )
        
        # 准备输出
        output = {
            "intent_analysis": IntentAnalysisOutput(
                roadmap_id="python-basics-test123",
                parsed_goal="学习Python基础",
                key_technologies=["Python"],
                difficulty_profile="beginner",
                time_constraint="10小时/周",
                recommended_focus=[],
                skill_gap_analysis=[],
                personalized_suggestions=[],
            ),
            "roadmap_id": "python-basics-test123",
        }
        
        # 执行
        await handler.handle(output, "test-task-id", mock_session)
        
        # 验证 live_step 被更新
        mock_state_manager.set_live_step.assert_called_once_with(
            "test-task-id",
            "intent_analysis",
        )
    
    # 注释：on_start/on_complete/on_error 已移除，由 SideEffectCoordinator 统一管理
    # 这些测试场景在 test_side_effect_coordinator.py 中覆盖


class TestContentHandler:
    """测试内容生成Handler"""
    
    @pytest.mark.asyncio
    async def test_handle_content_generation(
        self,
        mock_notification_service,
        mock_execution_logger,
        mock_state_manager,
        mock_session,
    ):
        """测试处理内容生成输出"""
        handler = ContentHandler(
            mock_notification_service,
            mock_execution_logger,
            mock_state_manager,
        )
        
        # 准备输出（包含教程、资源、测验引用）
        from app.models.domain import TutorialGenerationOutput
        output = {
            "tutorial_refs": {
                "concept-1": TutorialGenerationOutput(
                    concept_id="concept-1",
                    tutorial_id="tutorial-1",
                    content_url="https://example.com/tutorial",
                    summary="教程摘要",
                    sections=[],
                )
            },
            "resource_refs": {},
            "quiz_refs": {},
            "failed_concepts": [],
            "roadmap_id": "test-roadmap",
        }
        
        # 执行
        await handler.handle(output, "test-task-id", mock_session)
        
        # 验证 live_step 被更新
        mock_state_manager.set_live_step.assert_called_once_with(
            "test-task-id",
            "tutorial_generation",
        )
    
    @pytest.mark.asyncio
    async def test_on_complete_sends_workflow_completion(
        self,
        mock_notification_service,
        mock_execution_logger,
        mock_state_manager,
    ):
        """测试内容生成完成后发送工作流完成通知"""
        handler = ContentHandler(
            mock_notification_service,
            mock_execution_logger,
            mock_state_manager,
        )
        
        output = {
            "roadmap_id": "test-roadmap",
            "tutorial_refs": {"concept-1": MagicMock()},
            "failed_concepts": [],
        }
        
        # 执行
        await handler.on_complete("test-task-id", output, 5000)
        
        # 验证工作流完成通知被发送
        mock_notification_service.publish_completed.assert_called_once()
        args = mock_notification_service.publish_completed.call_args
        assert args.kwargs["task_id"] == "test-task-id"
        assert args.kwargs["roadmap_id"] == "test-roadmap"
        assert args.kwargs["tutorials_count"] == 1
        assert args.kwargs["failed_count"] == 0

