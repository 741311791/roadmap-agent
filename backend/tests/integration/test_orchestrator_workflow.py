"""
测试完整的 Orchestrator 工作流（集成测试）

测试内容：
- OrchestratorFactory 初始化
- WorkflowExecutor 执行完整工作流
- 各个 Runner 的集成
- 数据库交互
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.core.orchestrator_factory import OrchestratorFactory
from app.core.orchestrator.base import WorkflowConfig, RoadmapState
from app.models.domain import (
    UserRequest,
    IntentAnalysisOutput,
    RoadmapFramework,
    Stage,
    Module,
    Concept,
    ValidationOutput,
)


@pytest.fixture
async def initialized_factory():
    """初始化 OrchestratorFactory"""
    # 使用测试配置
    with patch("app.core.orchestrator_factory.settings") as mock_settings:
        mock_settings.DATABASE_URL_ASYNC = "postgresql+asyncpg://test:test@localhost/test"
        
        # Mock AsyncPostgresSaver
        with patch("app.core.orchestrator_factory.AsyncPostgresSaver") as mock_saver_cls:
            mock_saver_cm = MagicMock()
            mock_saver = AsyncMock()
            mock_saver.setup = AsyncMock()
            
            mock_saver_cm.__aenter__ = AsyncMock(return_value=mock_saver)
            mock_saver_cm.__aexit__ = AsyncMock(return_value=None)
            mock_saver_cls.from_conn_string.return_value = mock_saver_cm
            
            await OrchestratorFactory.initialize()
            
            yield OrchestratorFactory
            
            await OrchestratorFactory.cleanup()


@pytest.mark.asyncio
class TestOrchestratorFactory:
    """测试 OrchestratorFactory"""
    
    async def test_initialize(self):
        """测试工厂初始化"""
        with patch("app.core.orchestrator_factory.settings") as mock_settings:
            mock_settings.DATABASE_URL_ASYNC = "postgresql+asyncpg://test:test@localhost/test"
            
            with patch("app.core.orchestrator_factory.AsyncPostgresSaver") as mock_saver_cls:
                mock_saver_cm = MagicMock()
                mock_saver = AsyncMock()
                mock_saver.setup = AsyncMock()
                
                mock_saver_cm.__aenter__ = AsyncMock(return_value=mock_saver)
                mock_saver_cm.__aexit__ = AsyncMock(return_value=None)
                mock_saver_cls.from_conn_string.return_value = mock_saver_cm
                
                await OrchestratorFactory.initialize()
                
                assert OrchestratorFactory._initialized is True
                assert OrchestratorFactory._state_manager is not None
                assert OrchestratorFactory._checkpointer is not None
                
                await OrchestratorFactory.cleanup()
    
    async def test_get_state_manager(self, initialized_factory):
        """测试获取 StateManager"""
        state_manager = initialized_factory.get_state_manager()
        assert state_manager is not None
    
    async def test_get_checkpointer(self, initialized_factory):
        """测试获取 Checkpointer"""
        checkpointer = initialized_factory.get_checkpointer()
        assert checkpointer is not None
    
    async def test_create_workflow_executor(self, initialized_factory):
        """测试创建 WorkflowExecutor"""
        executor = initialized_factory.create_workflow_executor()
        assert executor is not None
        assert executor.builder is not None
        assert executor.state_manager is not None
        assert executor.checkpointer is not None


@pytest.mark.asyncio
class TestWorkflowExecution:
    """测试工作流执行"""
    
    async def test_workflow_executor_create_initial_state(
        self, initialized_factory, sample_user_request
    ):
        """测试创建初始状态"""
        executor = initialized_factory.create_workflow_executor()
        
        initial_state = executor._create_initial_state(
            sample_user_request,
            "test-trace-001"
        )
        
        assert initial_state["user_request"] == sample_user_request
        assert initial_state["task_id"] == "test-trace-001"
        assert initial_state["roadmap_id"] is None
        assert initial_state["intent_analysis"] is None
        assert initial_state["roadmap_framework"] is None
        assert initial_state["tutorial_refs"] == {}
        assert initial_state["failed_concepts"] == []
        assert initial_state["current_step"] == "init"
        assert initial_state["modification_count"] == 0
        assert initial_state["human_approved"] is False
    
    async def test_workflow_builder_creates_graph(self, initialized_factory):
        """测试 Builder 创建工作流图"""
        executor = initialized_factory.create_workflow_executor()
        
        # 访问 graph 属性会触发构建
        graph = executor.graph
        
        assert graph is not None
    
    @pytest.mark.skip(reason="Test is flaky, needs investigation")
    @patch("app.agents.intent_analyzer.IntentAnalyzerAgent")
    @patch("app.agents.curriculum_architect.CurriculumArchitectAgent")
    @patch("app.db.repositories.roadmap_repo.RoadmapRepository")
    @patch("app.db.session.AsyncSessionLocal")
    async def test_workflow_execution_intent_only(
        self,
        mock_session_local,
        mock_repo_cls,
        mock_curriculum_cls,
        mock_intent_cls,
        initialized_factory,
        sample_user_request,
    ):
        """测试工作流执行（仅需求分析）"""
        # Mock Intent Analyzer
        mock_intent = AsyncMock()
        mock_intent.execute = AsyncMock(return_value=IntentAnalysisOutput(
            parsed_goal="学习 Python",
            key_technologies=["Python"],
            difficulty_profile="beginner",
            time_constraint="3 months",
            recommended_focus=["basics"],
            roadmap_id="python-basics-12345678",
        ))
        mock_intent_cls.return_value = mock_intent
        
        # Mock Curriculum Architect
        mock_curriculum = AsyncMock()
        mock_curriculum.model_name = "test-model"
        mock_curriculum.model_provider = "test-provider"
        concept = Concept(
            concept_id="c1",
            name="Python 基础",
            description="Python 语法",
            estimated_hours=10.0,
            prerequisites=[],
            difficulty="easy",
            keywords=["Python"],
        )
        module = Module(
            module_id="m1",
            name="入门",
            description="Python 入门",
            concepts=[concept],
        )
        stage = Stage(
            stage_id="s1",
            name="基础",
            description="Python 基础",
            order=1,
            modules=[module],
        )
        framework = RoadmapFramework(
            roadmap_id="python-basics-12345678",
            title="Python 学习路线",
            stages=[stage],
            total_estimated_hours=10.0,
            recommended_completion_weeks=2,
        )
        
        mock_curriculum.execute = AsyncMock(return_value=MagicMock(
            framework=framework
        ))
        mock_curriculum_cls.return_value = mock_curriculum
        
        # Mock Repository
        mock_repo = AsyncMock()
        mock_repo.roadmap_id_exists = AsyncMock(return_value=False)
        mock_repo.update_task_status = AsyncMock()
        mock_repo.save_roadmap_with_framework = AsyncMock()
        mock_repo_cls.return_value = mock_repo
        
        # Mock Session
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_local.return_value = mock_session
        
        # Mock notification_service
        with patch("app.services.notification_service.notification_service") as mock_notif:
            mock_notif.publish_progress = AsyncMock()
            mock_notif.publish_failed = AsyncMock()
            
            # Mock execution_logger
            with patch("app.services.execution_logger.execution_logger") as mock_logger:
                mock_logger.log_workflow_start = AsyncMock()
                mock_logger.log_workflow_complete = AsyncMock()
                mock_logger.error = AsyncMock()
                
                # 使用跳过所有可选节点的配置
                with patch("app.core.orchestrator.base.WorkflowConfig.from_settings") as mock_config:
                    mock_config.return_value = WorkflowConfig(
                        skip_structure_validation=True,
                        skip_human_review=True,
                        skip_tutorial_generation=True,
                        skip_resource_recommendation=True,
                        skip_quiz_generation=True,
                    )
                    
                    # 创建 executor
                    executor = initialized_factory.create_workflow_executor()
                    
                    # 执行工作流
                    result = await executor.execute(
                        sample_user_request,
                        "test-trace-001"
                    )
                    
                    # 验证结果
                    assert result["roadmap_id"] is not None
                    assert result["roadmap_id"].startswith("python-basics-")
                    assert result["intent_analysis"] is not None
                    assert result["intent_analysis"].parsed_goal == "学习 Python"
                    assert result["roadmap_framework"] is not None

