"""
ValidationEditPlanRunner 单元测试

测试验证结果修改计划分析节点执行器
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.domain import (
    ValidationOutput,
    ValidationIssue,
    DimensionScore,
    EditPlan,
    EditIntent,
    EditPlanAnalyzerOutput,
    RoadmapFramework,
    LearningPreferences,
    UserRequest,
)
from app.core.orchestrator.node_runners.validation_edit_plan_runner import ValidationEditPlanRunner


class TestValidationEditPlanRunner:
    """测试 ValidationEditPlanRunner"""
    
    @pytest.fixture
    def mock_brain(self):
        """Mock WorkflowBrain"""
        brain = MagicMock()
        brain.node_execution = MagicMock(return_value=AsyncMock())
        # 使用 AsyncMock 作为 async context manager
        brain.node_execution.return_value.__aenter__ = AsyncMock(return_value=None)
        brain.node_execution.return_value.__aexit__ = AsyncMock(return_value=None)
        return brain
    
    @pytest.fixture
    def mock_agent_factory(self):
        """Mock AgentFactory"""
        factory = MagicMock()
        return factory
    
    @pytest.fixture
    def mock_edit_plan_analyzer_agent(self):
        """Mock EditPlanAnalyzerAgent"""
        agent = MagicMock()
        agent.execute = AsyncMock(return_value=EditPlanAnalyzerOutput(
            edit_plan=EditPlan(
                feedback_summary="验证发现循环依赖和无效前置关系问题",
                intents=[
                    EditIntent(
                        intent_type="modify",
                        target_type="concept",
                        target_id="c-1-1-2",
                        target_path="Stage 1 > Module 1 > Concept 2",
                        description="移除对不存在概念的前置依赖",
                        priority="must",
                    ),
                    EditIntent(
                        intent_type="modify",
                        target_type="concept",
                        target_id="c-1-1-3",
                        target_path="Stage 1 > Module 1 > Concept 3",
                        description="打破循环依赖链",
                        priority="must",
                    ),
                ],
                scope_analysis="影响 Stage 1 中的 2 个概念的前置关系",
                preservation_requirements=["Stage 2 完整保留", "所有概念的内容不变"],
            ),
            confidence=0.85,
            needs_clarification=False,
            clarification_questions=[],
        ))
        return agent
    
    @pytest.fixture
    def sample_validation_result(self) -> ValidationOutput:
        """示例验证结果（失败）"""
        return ValidationOutput(
            dimension_scores=[
                DimensionScore(dimension="knowledge_completeness", score=70.0, rationale="知识覆盖基本完整"),
            ],
            issues=[
                ValidationIssue(
                    severity="critical",
                    category="structural_flaw",
                    location="Stage 1 > Module 1 > Concept 2",
                    issue="前置概念 'c-invalid' 不存在",
                    suggestion="移除无效的前置关系",
                ),
                ValidationIssue(
                    severity="critical",
                    category="structural_flaw",
                    location="Stage 1",
                    issue="检测到循环依赖",
                    suggestion="打破循环依赖链",
                ),
            ],
            improvement_suggestions=[],
            overall_score=50.0,
            is_valid=False,
            validation_summary="验证未通过",
        )
    
    @pytest.fixture
    def sample_roadmap_framework(self) -> RoadmapFramework:
        """示例路线图框架"""
        return RoadmapFramework(
            roadmap_id="test-roadmap-123",
            title="测试路线图",
            stages=[],
            total_estimated_hours=100,
            recommended_completion_weeks=10,
        )
    
    @pytest.fixture
    def sample_user_preferences(self) -> LearningPreferences:
        """示例用户偏好"""
        return LearningPreferences(
            learning_goal="学习 Python 编程",
            current_level="beginner",
            available_hours_per_week=10,
        )
    
    @pytest.fixture
    def sample_state(
        self,
        sample_validation_result: ValidationOutput,
        sample_roadmap_framework: RoadmapFramework,
        sample_user_preferences: LearningPreferences,
    ) -> dict:
        """示例工作流状态"""
        return {
            "task_id": "task-123",
            "roadmap_id": "test-roadmap-123",
            "validation_result": sample_validation_result,
            "roadmap_framework": sample_roadmap_framework,
            "user_request": UserRequest(
                user_id="user-123",
                raw_input="学习 Python",
                preferences=sample_user_preferences,
            ),
        }
    
    @pytest.mark.asyncio
    async def test_run_success(
        self,
        mock_brain,
        mock_agent_factory,
        mock_edit_plan_analyzer_agent,
        sample_state,
    ):
        """测试正常执行流程"""
        # 配置 mock
        mock_agent_factory.create_edit_plan_analyzer.return_value = mock_edit_plan_analyzer_agent
        
        # 创建 runner
        runner = ValidationEditPlanRunner(
            brain=mock_brain,
            agent_factory=mock_agent_factory,
        )
        
        # 执行
        result = await runner.run(sample_state)
        
        # 验证结果
        assert "edit_plan" in result
        assert "user_feedback" in result
        assert result["edit_plan"] is not None
        assert len(result["edit_plan"].intents) == 2
        
        # 验证 agent 被调用
        mock_edit_plan_analyzer_agent.execute.assert_called_once()
        
        # 验证传入的 user_feedback 包含验证问题
        call_args = mock_edit_plan_analyzer_agent.execute.call_args
        input_data = call_args[0][0]
        assert "前置概念" in input_data.user_feedback
        assert "循环依赖" in input_data.user_feedback
    
    @pytest.mark.asyncio
    async def test_run_without_validation_result(
        self,
        mock_brain,
        mock_agent_factory,
    ):
        """测试没有 validation_result 时抛出异常"""
        runner = ValidationEditPlanRunner(
            brain=mock_brain,
            agent_factory=mock_agent_factory,
        )
        
        state = {
            "task_id": "task-123",
            "roadmap_framework": MagicMock(),
            "user_request": MagicMock(),
            # 缺少 validation_result
        }
        
        with pytest.raises(ValueError, match="validation_result 不存在"):
            await runner.run(state)
    
    @pytest.mark.asyncio
    async def test_run_without_roadmap_framework(
        self,
        mock_brain,
        mock_agent_factory,
    ):
        """测试没有 roadmap_framework 时抛出异常"""
        runner = ValidationEditPlanRunner(
            brain=mock_brain,
            agent_factory=mock_agent_factory,
        )
        
        state = {
            "task_id": "task-123",
            "validation_result": MagicMock(),
            "user_request": MagicMock(),
            # 缺少 roadmap_framework
        }
        
        with pytest.raises(ValueError, match="roadmap_framework 不存在"):
            await runner.run(state)
    
    @pytest.mark.asyncio
    async def test_format_validation_to_feedback_called(
        self,
        mock_brain,
        mock_agent_factory,
        mock_edit_plan_analyzer_agent,
        sample_state,
    ):
        """测试 format_validation_to_feedback 被正确调用"""
        mock_agent_factory.create_edit_plan_analyzer.return_value = mock_edit_plan_analyzer_agent
        
        runner = ValidationEditPlanRunner(
            brain=mock_brain,
            agent_factory=mock_agent_factory,
        )
        
        result = await runner.run(sample_state)
        
        # 验证 user_feedback 包含格式化后的验证问题
        user_feedback = result["user_feedback"]
        
        # 验证包含关键信息
        assert "验证未通过" in user_feedback
        assert "50/100" in user_feedback
        assert "必须修复的问题" in user_feedback


class TestValidationEditPlanRunnerIntegration:
    """集成测试（使用真实的 format_validation_to_feedback）"""
    
    def test_format_validation_produces_valid_feedback(self):
        """测试格式化函数产生的 feedback 能被 EditPlanAnalyzerAgent 使用"""
        from app.utils.validation_formatter import format_validation_to_feedback
        
        validation_output = ValidationOutput(
            dimension_scores=[
                DimensionScore(dimension="knowledge_completeness", score=60.0, rationale="缺少关键概念"),
            ],
            issues=[
                ValidationIssue(
                    severity="critical",
                    category="structural_flaw",
                    location="Stage 2 > Module 1",
                    issue="模块不包含任何概念",
                    suggestion="添加至少一个概念或删除该模块",
                ),
            ],
            improvement_suggestions=[],
            overall_score=45.0,
            is_valid=False,
            validation_summary="验证未通过",
        )
        
        feedback = format_validation_to_feedback(validation_output)
        
        # 验证反馈格式
        assert isinstance(feedback, str)
        assert len(feedback) > 0
        
        # 验证包含问题信息
        assert "模块不包含任何概念" in feedback
        assert "critical" in feedback.lower() or "必须" in feedback
        
        # 验证包含建议
        assert "添加至少一个概念" in feedback or "删除该模块" in feedback

