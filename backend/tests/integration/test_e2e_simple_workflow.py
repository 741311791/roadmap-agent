"""
简化的端到端工作流测试

测试目标：
- 验证新架构的各个组件可以正确协同工作
- 不依赖真实数据库，使用内存 mock
- 测试核心工作流路径
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.orchestrator.base import WorkflowConfig
from app.core.orchestrator.state_manager import StateManager
from app.core.orchestrator.routers import WorkflowRouter
from app.core.orchestrator.node_runners.intent_runner import IntentAnalysisRunner
from app.core.orchestrator.node_runners.curriculum_runner import CurriculumDesignRunner
from app.models.domain import (
    UserRequest,
    IntentAnalysisOutput,
    RoadmapFramework,
    Stage,
    Module,
    Concept,
)


class TestSimpleWorkflow:
    """测试简化的工作流"""
    
    @pytest.mark.asyncio
    async def test_intent_runner_execution(self, sample_user_request):
        """测试 IntentAnalysisRunner 单独执行"""
        state_manager = StateManager()
        
        # Mock Agent 和 AgentFactory
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value=IntentAnalysisOutput(
            parsed_goal="学习 Python",
            key_technologies=["Python"],
            difficulty_profile="beginner",
            time_constraint="3 months",
            recommended_focus=["basics"],
            roadmap_id="python-basics-12345678",
        ))
        
        mock_factory = MagicMock()
        mock_factory.create_intent_analyzer = MagicMock(return_value=mock_agent)
        
        runner = IntentAnalysisRunner(state_manager, mock_factory)
        
        # Mock Repository
        with patch("app.db.session.AsyncSessionLocal") as mock_session_local:
                mock_session = AsyncMock()
                mock_session.commit = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_local.return_value = mock_session
                
                with patch("app.db.repositories.roadmap_repo.RoadmapRepository") as mock_repo_cls:
                    mock_repo = AsyncMock()
                    mock_repo.roadmap_id_exists = AsyncMock(return_value=False)
                    mock_repo.update_task_status = AsyncMock()
                    mock_repo_cls.return_value = mock_repo
                    
                    # Mock services
                    with patch("app.services.notification_service.notification_service") as mock_notif:
                        mock_notif.publish_progress = AsyncMock()
                        
                        with patch("app.services.execution_logger.execution_logger") as mock_logger:
                            mock_logger.log_workflow_start = AsyncMock()
                            mock_logger.log_workflow_complete = AsyncMock()
                            
                            # 创建初始状态
                            initial_state = {
                                "user_request": sample_user_request,
                                "task_id": "test-trace-001",
                                "roadmap_id": None,
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
                            
                            # 执行 Runner
                            result = await runner.run(initial_state)
                            
                            # 验证结果
                            assert result["roadmap_id"] is not None
                            assert result["roadmap_id"].startswith("python-basics-")
                            assert result["intent_analysis"] is not None
                            assert result["intent_analysis"].parsed_goal == "学习 Python"
                            assert result["current_step"] == "intent_analysis"
                            assert "需求分析完成" in result["execution_history"]
    
    @pytest.mark.asyncio
    async def test_curriculum_runner_execution(self, sample_user_request):
        """测试 CurriculumDesignRunner 单独执行"""
        state_manager = StateManager()
        
        # 创建 intent_analysis
        intent_analysis = IntentAnalysisOutput(
            parsed_goal="学习 Python",
            key_technologies=["Python"],
            difficulty_profile="beginner",
            time_constraint="3 months",
            recommended_focus=["basics"],
            roadmap_id="python-basics-12345678",
        )
        
        # 创建 framework
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
        
        # Mock Agent 和 AgentFactory
        mock_agent = AsyncMock()
        mock_agent.model_name = "test-model"
        mock_agent.model_provider = "test-provider"
        mock_agent.execute = AsyncMock(return_value=MagicMock(framework=framework))
        
        mock_factory = MagicMock()
        mock_factory.create_curriculum_architect = MagicMock(return_value=mock_agent)
        
        runner = CurriculumDesignRunner(state_manager, mock_factory)
        
        # Mock Repository
        with patch("app.db.session.AsyncSessionLocal") as mock_session_local:
                mock_session = AsyncMock()
                mock_session.commit = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                mock_session_local.return_value = mock_session
                
                with patch("app.db.repositories.roadmap_repo.RoadmapRepository") as mock_repo_cls:
                    mock_repo = AsyncMock()
                    mock_repo.save_roadmap_with_framework = AsyncMock()
                    mock_repo_cls.return_value = mock_repo
                    
                    # Mock services
                    with patch("app.services.notification_service.notification_service") as mock_notif:
                        mock_notif.publish_progress = AsyncMock()
                        
                        with patch("app.services.execution_logger.execution_logger") as mock_logger:
                            mock_logger.log_workflow_start = AsyncMock()
                            mock_logger.log_workflow_complete = AsyncMock()
                            
                            # 创建状态
                            state = {
                                "user_request": sample_user_request,
                                "task_id": "test-trace-001",
                                "roadmap_id": "python-basics-12345678",
                                "intent_analysis": intent_analysis,
                                "roadmap_framework": None,
                                "validation_result": None,
                                "tutorial_refs": {},
                                "resource_refs": {},
                                "quiz_refs": {},
                                "failed_concepts": [],
                                "current_step": "intent_analysis",
                                "modification_count": 0,
                                "human_approved": False,
                                "execution_history": [],
                            }
                            
                            # 执行 Runner
                            result = await runner.run(state)
                            
                            # 验证结果
                            assert result["roadmap_framework"] is not None
                            assert result["roadmap_framework"].roadmap_id == "python-basics-12345678"
                            assert result["current_step"] == "curriculum_design"
                            assert "课程架构设计完成" in result["execution_history"]
    
    def test_state_manager_integration(self):
        """测试 StateManager 集成"""
        manager = StateManager()
        
        # 模拟工作流执行过程中的状态变化
        manager.set_live_step("trace-1", "intent_analysis")
        assert manager.get_live_step("trace-1") == "intent_analysis"
        
        manager.set_live_step("trace-1", "curriculum_design")
        assert manager.get_live_step("trace-1") == "curriculum_design"
        
        manager.set_live_step("trace-1", "tutorial_generation")
        assert manager.get_live_step("trace-1") == "tutorial_generation"
        
        # 清除
        manager.clear_live_step("trace-1")
        assert manager.get_live_step("trace-1") is None
    
    def test_workflow_config_integration(self):
        """测试 WorkflowConfig 集成"""
        # 测试不同配置组合
        configs = [
            WorkflowConfig(),  # 默认：全部启用
            WorkflowConfig(skip_structure_validation=True),  # 跳过验证
            WorkflowConfig(skip_human_review=True),  # 跳过人工审核
            WorkflowConfig(
                skip_structure_validation=True,
                skip_human_review=True,
                skip_tutorial_generation=True,
            ),  # 最小配置
        ]
        
        for config in configs:
            # 所有配置都应该能成功创建
            assert config is not None
            assert config.max_framework_retry >= 1
            assert config.parallel_tutorial_limit >= 1
    
    def test_router_integration_scenarios(self, sample_roadmap_framework):
        """测试 Router 各种场景"""
        config = WorkflowConfig()
        router = WorkflowRouter(config)
        
        # 场景1：验证通过，进入人工审核
        state1 = {
            "task_id": "test",
            "validation_result": MagicMock(is_valid=True),
            "modification_count": 0,
        }
        assert router.route_after_validation(state1) == "human_review"
        
        # 场景2：验证失败，重试
        state2 = {
            "task_id": "test",
            "validation_result": MagicMock(is_valid=False),
            "modification_count": 1,
        }
        assert router.route_after_validation(state2) == "edit_roadmap"
        
        # 场景3：人工审核批准
        state3 = {
            "task_id": "test",
            "human_approved": True,
        }
        assert router.route_after_human_review(state3) == "approved"
        
        # 场景4：人工审核拒绝
        state4 = {
            "task_id": "test",
            "human_approved": False,
        }
        assert router.route_after_human_review(state4) == "modify"

