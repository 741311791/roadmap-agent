"""
Node纯函数单元测试

测试所有Node的业务逻辑，无需Mock数据库
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.orchestrator.base import RoadmapState
from app.core.orchestrator.runtime_context import RuntimeContext
from app.core.orchestrator.nodes import (
    intent_analysis_node,
    curriculum_design_node,
    structure_validation_node,
    roadmap_edit_node,
    human_review_node,
)
from app.models.domain import (
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
        learning_goal="学习Python",
        current_level="beginner",
        available_hours_per_week=10,
        preferences={},
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
        from app.models.domain import Stage, Module, Concept
        mock_framework = RoadmapFramework(
            title="Python学习路线图",
            description="从零开始学习Python",
            stages=[
                Stage(
                    stage_id="stage-1",
                    title="基础阶段",
                    description="学习Python基础",
                    order_index=1,
                    estimated_duration_hours=40,
                    modules=[
                        Module(
                            module_id="module-1",
                            title="Python语法",
                            description="Python基础语法",
                            order_index=1,
                            estimated_duration_hours=20,
                            concepts=[
                                Concept(
                                    concept_id="concept-1",
                                    name="变量和数据类型",
                                    description="学习变量定义和基本数据类型",
                                    order_index=1,
                                    estimated_duration_hours=5,
                                    difficulty_level="easy",
                                    prerequisites=[],
                                )
                            ],
                        )
                    ],
                )
            ],
            estimated_total_hours=40,
            difficulty_distribution={"easy": 100},
        )
        mock_agent.design = AsyncMock(return_value=mock_framework)
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
            title="测试路线图",
            description="测试",
            stages=[
                Stage(
                    stage_id="stage-1",
                    title="阶段1",
                    description="描述",
                    order_index=1,
                    estimated_duration_hours=10,
                    modules=[
                        Module(
                            module_id="module-1",
                            title="模块1",
                            description="描述",
                            order_index=1,
                            estimated_duration_hours=10,
                            concepts=[
                                Concept(
                                    concept_id="concept-1",
                                    name="概念1",
                                    description="描述",
                                    order_index=1,
                                    estimated_duration_hours=5,
                                    difficulty_level="easy",
                                    prerequisites=[],
                                )
                            ],
                        )
                    ],
                )
            ],
            estimated_total_hours=10,
            difficulty_distribution={"easy": 100},
        )
        
        state: RoadmapState = {
            "task_id": "test-task-id",
            "roadmap_id": "test-roadmap",
            "roadmap_framework": framework,
            "validation_round": 0,
        }
        
        # Mock Agent
        mock_agent = AsyncMock()
        from app.models.domain import ValidationIssue, DimensionScore, ImprovementSuggestion
        mock_validation = ValidationOutput(
            is_valid=True,
            overall_score=95.0,
            issues=[],
            dimension_scores=[
                DimensionScore(
                    dimension="structure",
                    score=95.0,
                    feedback="结构合理",
                )
            ],
            improvement_suggestions=[],
            validation_summary="验证通过",
        )
        mock_agent.validate = AsyncMock(return_value=mock_validation)
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
        """测试人工审核批准场景"""
        # 准备
        state: RoadmapState = {
            "task_id": "test-task-id",
            "roadmap_id": "test-roadmap",
        }
        
        # Mock interrupt返回值（模拟用户批准）
        from unittest.mock import patch
        with patch("app.core.orchestrator.nodes.human_review.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {
                "approved": True,
                "feedback": "",
            }
            
            # 执行
            result = await human_review_node(state, mock_config)
            
            # 验证
            assert result["human_approved"] is True
            assert result["user_feedback"] is None
            assert result["current_step"] == "human_review"
    
    @pytest.mark.asyncio
    async def test_human_review_rejected(self, mock_config):
        """测试人工审核拒绝场景"""
        # 准备
        state: RoadmapState = {
            "task_id": "test-task-id",
            "roadmap_id": "test-roadmap",
        }
        
        # Mock interrupt返回值（模拟用户拒绝）
        from unittest.mock import patch
        with patch("app.core.orchestrator.nodes.human_review.interrupt") as mock_interrupt:
            mock_interrupt.return_value = {
                "approved": False,
                "feedback": "需要调整难度",
            }
            
            # 执行
            result = await human_review_node(state, mock_config)
            
            # 验证
            assert result["human_approved"] is False
            assert result["user_feedback"] == "需要调整难度"
            assert result["current_step"] == "human_review"

