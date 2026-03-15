"""
Node纯函数单元测试

测试所有Node的业务逻辑，无需Mock数据库
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.orchestrator.base import RoadmapState, WorkflowConfig
from app.core.orchestrator.routers import WorkflowRouter
from app.core.orchestrator.runtime_context import RuntimeContext
from app.core.orchestrator.nodes import (
    intent_analysis_node,
    curriculum_design_node,
    structure_validation_node,
    roadmap_edit_node,
    human_review_node,
    auto_content_generation_node,
)
from app.models.domain import (
    LearningPreferences,
    UserRequest,
    IntentAnalysisOutput,
    RoadmapFramework,
    ValidationOutput,
    EditPlan,
)


@pytest.fixture
def mock_runtime_context():
    """创建Mock的RuntimeContext"""
    context = MagicMock(spec=RuntimeContext)
    context.agent_factory = MagicMock()
    context.notification_service = AsyncMock()
    context.execution_logger = AsyncMock()
    context.state_manager = AsyncMock()
    return context


@pytest.fixture
def mock_config(mock_runtime_context):
    """创建Mock的RunnableConfig"""
    return {
        "configurable": {
            "thread_id": "test-task-id",
            "runtime_context": mock_runtime_context,
        }
    }


@pytest.fixture
def sample_user_request():
    """示例用户请求"""
    return UserRequest(
        user_id="test-user",
        session_id="test-session-id",
        preferences=LearningPreferences(
            learning_goal="学习Python",
            current_level="beginner",
            available_hours_per_week=10,
            motivation="个人兴趣",
            career_background="零基础转行",
        ),
    )


class TestIntentAnalysisNode:
    """测试意图分析节点"""
    
    @pytest.mark.asyncio
    async def test_intent_analysis_success(
        self,
        mock_config,
        mock_runtime_context,
        sample_user_request,
    ):
        """测试意图分析成功场景"""
        # 准备
        state: RoadmapState = {
            "task_id": "test-task-id",
            "user_request": sample_user_request,
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
        
        # Mock Agent
        mock_agent = AsyncMock()
        mock_agent.execute = AsyncMock(return_value=IntentAnalysisOutput(
            roadmap_id="python-basics-test123",
            parsed_goal="学习Python基础",
            key_technologies=["Python", "FastAPI"],
            difficulty_profile="beginner",
            time_constraint="10小时/周",
            recommended_focus=["语法基础", "Web开发"],
            skill_gap_analysis=[],
            personalized_suggestions=[],
        ))
        mock_runtime_context.agent_factory.create_intent_analyzer.return_value = mock_agent
        
        # 执行
        result = await intent_analysis_node(state, mock_config)
        
        # 验证
        assert result["roadmap_id"] == "python-basics-test123"
        assert result["current_step"] == "intent_analysis"
        assert result["intent_analysis"] is not None
        assert "需求分析完成" in result["execution_history"]
        
        # 验证Agent被调用
        mock_agent.execute.assert_called_once_with(sample_user_request)


class TestCurriculumDesignNode:
    """测试课程设计节点"""
    
    @pytest.mark.asyncio
    async def test_curriculum_design_success(
        self,
        mock_config,
        mock_runtime_context,
        sample_user_request,
    ):
        """测试课程设计成功场景"""
        # 准备
        intent_analysis = IntentAnalysisOutput(
            roadmap_id="test-roadmap",
            parsed_goal="学习Python",
            key_technologies=["Python"],
            difficulty_profile="beginner",
            time_constraint="10小时/周",
            recommended_focus=[],
            skill_gap_analysis=[],
            personalized_suggestions=[],
        )
        
        state: RoadmapState = {
            "task_id": "test-task-id",
            "user_request": sample_user_request,
            "roadmap_id": "test-roadmap",
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
        
        # Mock Agent
        mock_agent = AsyncMock()
        from app.models.domain import CurriculumDesignOutput, Stage, Module, Concept
        mock_framework = RoadmapFramework(
            roadmap_id="test-roadmap",
            title="Python学习路线图",
            stages=[
                Stage(
                    stage_id="stage-1",
                    name="基础阶段",
                    description="学习Python基础",
                    order=1,
                    modules=[
                        Module(
                            module_id="module-1",
                            name="Python语法",
                            description="Python基础语法",
                            concepts=[
                                Concept(
                                    concept_id="concept-1",
                                    name="变量和数据类型",
                                    description="学习变量定义和基本数据类型",
                                    estimated_hours=5,
                                    difficulty="easy",
                                    prerequisites=[],
                                )
                            ],
                        )
                    ],
                )
            ],
            total_estimated_hours=40,
            recommended_completion_weeks=4,
        )
        mock_agent.execute = AsyncMock(
            return_value=CurriculumDesignOutput(framework=mock_framework)
        )
        mock_runtime_context.agent_factory.create_curriculum_architect.return_value = mock_agent
        
        # 执行
        result = await curriculum_design_node(state, mock_config)
        
        # 验证
        assert result["roadmap_framework"] is not None
        assert result["current_step"] == "curriculum_design"
        assert "课程设计完成" in result["execution_history"]
        assert result["roadmap_framework"].title == "Python学习路线图"


class TestStructureValidationNode:
    """测试结构验证节点"""
    
    @pytest.mark.asyncio
    async def test_validation_pass(
        self,
        mock_config,
        mock_runtime_context,
    ):
        """测试验证通过场景"""
        # 准备
        from app.models.domain import Stage, Module, Concept
        framework = RoadmapFramework(
            roadmap_id="test-roadmap",
            title="测试路线图",
            stages=[
                Stage(
                    stage_id="stage-1",
                    name="阶段1",
                    description="描述",
                    order=1,
                    modules=[
                        Module(
                            module_id="module-1",
                            name="模块1",
                            description="描述",
                            concepts=[
                                Concept(
                                    concept_id="concept-1",
                                    name="概念1",
                                    description="描述",
                                    estimated_hours=5,
                                    difficulty="easy",
                                    prerequisites=[],
                                )
                            ],
                        )
                    ],
                )
            ],
            total_estimated_hours=10,
            recommended_completion_weeks=1,
        )
        
        state: RoadmapState = {
            "task_id": "test-task-id",
            "roadmap_id": "test-roadmap",
            "roadmap_framework": framework,
            "validation_round": 0,
            "user_request": UserRequest(
                user_id="test-user",
                session_id="test-session-id",
                preferences=LearningPreferences(
                    learning_goal="学习Python",
                    current_level="beginner",
                    available_hours_per_week=10,
                    motivation="个人兴趣",
                    career_background="零基础转行",
                ),
            ),
        }
        
        # Mock Agent
        mock_agent = AsyncMock()
        from app.models.domain import DimensionScore
        mock_validation = ValidationOutput(
            is_valid=True,
            overall_score=95.0,
            issues=[],
            dimension_scores=[
                DimensionScore(
                    dimension="structure",
                    score=95.0,
                    rationale="结构合理",
                )
            ],
            improvement_suggestions=[],
            validation_summary="验证通过",
        )
        mock_agent.execute = AsyncMock(return_value=mock_validation)
        mock_runtime_context.agent_factory.create_structure_validator.return_value = mock_agent
        
        # 执行
        result = await structure_validation_node(state, mock_config)
        
        # 验证
        assert result["validation_result"].is_valid is True
        assert result["validation_result"].overall_score == 95.0
        assert result["validation_round"] == 1
        assert result["current_step"] == "structure_validation"


class TestHumanReviewNode:
    """测试人工审核节点"""

    @pytest.mark.asyncio
    async def test_human_review_approved(self, mock_config):
        """测试人工审核批准场景——应触发内容生成并返回 content_generation_queued"""
        state: RoadmapState = {
            "task_id": "test-task-id",
            "roadmap_id": "test-roadmap",
        }

        with (
            patch("app.core.orchestrator.nodes.human_review.interrupt") as mock_interrupt,
            patch("app.core.orchestrator.nodes.human_review.trigger_content_generation", new_callable=AsyncMock) as mock_trigger,
        ):
            mock_interrupt.return_value = {"approved": True, "feedback": ""}
            mock_trigger.return_value = "celery-task-id-123"

            result = await human_review_node(state, mock_config)

            assert result["human_approved"] is True
            assert result["user_feedback"] is None
            assert result["current_step"] == "content_generation_queued"
            mock_trigger.assert_called_once_with(
                task_id="test-task-id",
                roadmap_id="test-roadmap",
                user_id=None,
                state=state,
            )

    @pytest.mark.asyncio
    async def test_human_review_rejected(self, mock_config):
        """测试人工审核拒绝场景——不触发内容生成，返回 human_review"""
        state: RoadmapState = {
            "task_id": "test-task-id",
            "roadmap_id": "test-roadmap",
        }

        with patch("app.core.orchestrator.nodes.human_review.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {"approved": False, "feedback": "需要调整难度"}

            result = await human_review_node(state, mock_config)

            assert result["human_approved"] is False
            assert result["user_feedback"] == "需要调整难度"
            assert result["current_step"] == "human_review"


class TestAutoContentGenerationNode:
    """测试极速模式自动内容生成节点"""

    @pytest.fixture
    def turbo_state(self):
        """极速模式下的典型工作流状态"""
        from app.models.domain import UserRequest, LearningPreferences
        user_req = UserRequest(
            user_id="test-user",
            session_id="test-task-id",
            preferences=LearningPreferences(
                learning_goal="学习Python",
                available_hours_per_week=10,
                motivation="Personal interest",
                current_level="beginner",
                career_background="Not specified",
            ),
            turbo_mode=True,
        )
        return {
            "task_id": "test-task-id",
            "roadmap_id": "test-roadmap",
            "user_request": user_req,
        }

    @pytest.mark.asyncio
    async def test_auto_content_generation_success(self, mock_config, turbo_state):
        """正常情况：触发内容生成后返回 content_generation_queued"""
        with patch(
            "app.core.orchestrator.nodes.auto_content_generation.trigger_content_generation",
            new_callable=AsyncMock,
        ) as mock_trigger:
            mock_trigger.return_value = "celery-task-456"

            result = await auto_content_generation_node(turbo_state, mock_config)

            assert result["current_step"] == "content_generation_queued"
            assert result["human_approved"] is True
            assert result["roadmap_id"] == "test-roadmap"
            mock_trigger.assert_called_once_with(
                task_id="test-task-id",
                roadmap_id="test-roadmap",
                user_id="test-user",
                state=turbo_state,
            )

    @pytest.mark.asyncio
    async def test_auto_content_generation_trigger_failure(self, mock_config, turbo_state):
        """触发失败时：仍然返回 content_generation_queued，不将异常向上传播"""
        with patch(
            "app.core.orchestrator.nodes.auto_content_generation.trigger_content_generation",
            new_callable=AsyncMock,
        ) as mock_trigger:
            mock_trigger.side_effect = Exception("Celery 连接失败")

            result = await auto_content_generation_node(turbo_state, mock_config)

            assert result["current_step"] == "content_generation_queued"
            assert result["human_approved"] is True

    @pytest.mark.asyncio
    async def test_auto_content_generation_missing_roadmap_id(self, mock_config):
        """roadmap_id 缺失时：提前返回，不调用 trigger"""
        state: RoadmapState = {
            "task_id": "test-task-id",
            "roadmap_id": None,
        }

        with patch(
            "app.core.orchestrator.nodes.auto_content_generation.trigger_content_generation",
            new_callable=AsyncMock,
        ) as mock_trigger:
            result = await auto_content_generation_node(state, mock_config)

            assert result["current_step"] == "content_generation_queued"
            assert result["human_approved"] is True
            mock_trigger.assert_not_called()


class TestWorkflowRouterCurriculum:
    """测试 curriculum_design 后的路由逻辑"""

    def _make_config(self, skip_human_review: bool = False) -> WorkflowConfig:
        return WorkflowConfig(skip_human_review=skip_human_review, max_framework_retry=3)

    def _make_state(self, turbo_mode: bool) -> RoadmapState:
        from app.models.domain import UserRequest, LearningPreferences
        user_req = UserRequest(
            user_id="u1",
            session_id="s1",
            preferences=LearningPreferences(
                learning_goal="学习Python",
                available_hours_per_week=10,
                motivation="Personal interest",
                current_level="beginner",
                career_background="Not specified",
            ),
            turbo_mode=turbo_mode,
        )
        return {"task_id": "t1", "user_request": user_req}

    def test_turbo_mode_routes_to_auto_content_generation(self):
        """极速模式：curriculum 后应路由到 auto_content_generation"""
        router = WorkflowRouter(self._make_config())
        state = self._make_state(turbo_mode=True)

        result = router.route_after_curriculum(state)

        assert result == "auto_content_generation"

    def test_normal_mode_routes_to_structure_validation(self):
        """普通模式：curriculum 后应路由到 structure_validation"""
        router = WorkflowRouter(self._make_config())
        state = self._make_state(turbo_mode=False)

        result = router.route_after_curriculum(state)

        assert result == "structure_validation"

    def test_no_user_request_defaults_to_auto_content_generation(self):
        """缺少 user_request 时默认极速模式（turbo_mode 默认为 True）"""
        router = WorkflowRouter(self._make_config())
        state: RoadmapState = {"task_id": "t1"}

        result = router.route_after_curriculum(state)

        assert result == "auto_content_generation"

