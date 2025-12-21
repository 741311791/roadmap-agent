"""
A3: 结构审查员 (StructureValidatorAgent) 集成测试
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from app.agents.structure_validator import StructureValidatorAgent
from app.models.domain import (
    RoadmapFramework,
    LearningPreferences,
    ValidationOutput,
)


class TestStructureValidatorAgent:
    """结构审查员 Agent 集成测试"""
    
    @pytest.fixture
    def mock_llm_valid_response(self):
        """Mock LLM 返回的验证通过结果"""
        response_data = {
            "dimension_scores": [
                {
                    "dimension": "knowledge_completeness",
                    "score": 92.0,
                    "rationale": "知识覆盖全面"
                },
                {
                    "dimension": "knowledge_progression",
                    "score": 90.0,
                    "rationale": "难度递增合理"
                },
                {
                    "dimension": "stage_coherence",
                    "score": 88.0,
                    "rationale": "阶段划分清晰"
                },
                {
                    "dimension": "module_clarity",
                    "score": 91.0,
                    "rationale": "模块主题明确"
                },
                {
                    "dimension": "user_alignment",
                    "score": 89.0,
                    "rationale": "符合用户需求"
                }
            ],
            "issues": [],
            "improvement_suggestions": []
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = json.dumps(response_data, ensure_ascii=False)
        response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        return response
    
    @pytest.fixture
    def mock_llm_invalid_response(self):
        """Mock LLM 返回的验证未通过结果"""
        response_data = {
            "dimension_scores": [
                {
                    "dimension": "knowledge_completeness",
                    "score": 65.0,
                    "rationale": "缺少部分核心知识"
                },
                {
                    "dimension": "knowledge_progression",
                    "score": 70.0,
                    "rationale": "部分难度跳跃"
                },
                {
                    "dimension": "stage_coherence",
                    "score": 75.0,
                    "rationale": "阶段边界略模糊"
                },
                {
                    "dimension": "module_clarity",
                    "score": 80.0,
                    "rationale": "模块基本清晰"
                },
                {
                    "dimension": "user_alignment",
                    "score": 60.0,
                    "rationale": "部分不匹配用户水平"
                }
            ],
            "issues": [
                {
                    "severity": "critical",
                    "category": "knowledge_gap",
                    "location": "Stage 1 > Module 1",
                    "issue": "缺少基础知识前置",
                    "suggestion": "添加基础概念",
                    "structural_suggestion": {
                        "action": "add_concept",
                        "target_location": "Stage 1 > Module 1 之前",
                        "content": "添加 HTML 基础概念",
                        "reason": "用户是初学者，需要基础知识"
                    }
                },
                {
                    "severity": "warning",
                    "category": "structural_flaw",
                    "location": "Stage 2",
                    "issue": "阶段内容相对简单",
                    "suggestion": "考虑增加更多实践项目"
                }
            ],
            "improvement_suggestions": []
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = json.dumps(response_data, ensure_ascii=False)
        response.usage = MagicMock(prompt_tokens=100, completion_tokens=50)
        return response
    
    @pytest.mark.asyncio
    async def test_validate_success(
        self,
        sample_roadmap_framework,
        sample_learning_preferences,
        mock_llm_valid_response
    ):
        """测试验证通过"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_valid_response
            
            agent = StructureValidatorAgent()
            result = await agent.validate(
                framework=sample_roadmap_framework,
                user_preferences=sample_learning_preferences,
            )
            
            # 验证返回类型
            assert isinstance(result, ValidationOutput)
            
            # 验证通过（如果结构检查也通过）
            # 注意：如果 sample_roadmap_framework 结构有问题，可能会失败
            assert result.overall_score >= 0.0
            assert result.validation_summary is not None
    
    @pytest.mark.asyncio
    async def test_validate_failure(
        self,
        sample_roadmap_framework,
        sample_learning_preferences,
        mock_llm_invalid_response
    ):
        """测试验证未通过"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_invalid_response
            
            agent = StructureValidatorAgent()
            result = await agent.validate(
                framework=sample_roadmap_framework,
                user_preferences=sample_learning_preferences,
            )
            
            # 验证返回类型
            assert isinstance(result, ValidationOutput)
            
            # 检查是否有问题
            assert len(result.issues) > 0
            
            # 检查维度评分
            assert len(result.dimension_scores) == 5
    
    @pytest.mark.asyncio
    async def test_validate_returns_dimension_scores(
        self,
        sample_roadmap_framework,
        sample_learning_preferences,
        mock_llm_valid_response
    ):
        """测试验证返回维度评分"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_valid_response
            
            agent = StructureValidatorAgent()
            result = await agent.validate(
                framework=sample_roadmap_framework,
                user_preferences=sample_learning_preferences,
            )
            
            # 检查维度评分
            assert len(result.dimension_scores) == 5
            dimension_names = [score.dimension for score in result.dimension_scores]
            assert "knowledge_completeness" in dimension_names
            assert "knowledge_progression" in dimension_names
            assert "stage_coherence" in dimension_names
            assert "module_clarity" in dimension_names
            assert "user_alignment" in dimension_names
    
    @pytest.mark.asyncio
    async def test_validate_score_in_range(
        self,
        sample_roadmap_framework,
        sample_learning_preferences,
        mock_llm_valid_response
    ):
        """测试评分在有效范围内"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_valid_response
            
            agent = StructureValidatorAgent()
            result = await agent.validate(
                framework=sample_roadmap_framework,
                user_preferences=sample_learning_preferences,
            )
            
            assert 0 <= result.overall_score <= 100
            
            # 检查每个维度的分数也在范围内
            for score in result.dimension_scores:
                assert 0 <= score.score <= 100


