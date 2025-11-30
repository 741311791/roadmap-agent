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
            "is_valid": True,
            "issues": [],
            "overall_score": 92.5
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = f"```json\n{json.dumps(response_data, ensure_ascii=False)}\n```"
        return response
    
    @pytest.fixture
    def mock_llm_invalid_response(self):
        """Mock LLM 返回的验证未通过结果"""
        response_data = {
            "is_valid": False,
            "issues": [
                {
                    "severity": "critical",
                    "location": "Stage 1 > Module 1 > Concept 2",
                    "issue": "CSS 概念缺少 HTML 基础作为前置依赖",
                    "suggestion": "将 HTML 基础 (c1) 添加为 CSS 基础 (c2) 的前置概念"
                },
                {
                    "severity": "warning",
                    "location": "Stage 1",
                    "issue": "阶段内容相对简单，可能无法满足学习目标",
                    "suggestion": "考虑增加更多实践项目和进阶内容"
                }
            ],
            "overall_score": 68.0
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = f"```json\n{json.dumps(response_data, ensure_ascii=False)}\n```"
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
            
            # 验证通过
            assert result.is_valid is True
            assert len(result.issues) == 0
            assert result.overall_score >= 90.0
    
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
            
            # 验证未通过
            assert result.is_valid is False
            assert len(result.issues) > 0
            assert result.overall_score < 90.0
    
    @pytest.mark.asyncio
    async def test_validate_returns_issues_with_severity(
        self,
        sample_roadmap_framework,
        sample_learning_preferences,
        mock_llm_invalid_response
    ):
        """测试验证问题包含严重程度"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_invalid_response
            
            agent = StructureValidatorAgent()
            result = await agent.validate(
                framework=sample_roadmap_framework,
                user_preferences=sample_learning_preferences,
            )
            
            # 检查问题的严重程度
            severities = [issue.severity for issue in result.issues]
            assert "critical" in severities or "warning" in severities
    
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

