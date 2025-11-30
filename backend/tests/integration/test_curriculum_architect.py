"""
A2: 课程架构师 (CurriculumArchitectAgent) 集成测试
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.models.domain import (
    IntentAnalysisOutput,
    LearningPreferences,
    CurriculumDesignOutput,
    RoadmapFramework,
)


class TestCurriculumArchitectAgent:
    """课程架构师 Agent 集成测试"""
    
    @pytest.fixture
    def mock_llm_curriculum_response(self):
        """Mock LLM 返回的课程设计结果"""
        response_data = {
            "framework": {
                "roadmap_id": "roadmap-test-001",
                "title": "Python Web 开发学习路线",
                "stages": [
                    {
                        "stage_id": "s1",
                        "name": "Python 基础",
                        "description": "学习 Python 编程基础",
                        "order": 1,
                        "modules": [
                            {
                                "module_id": "m1",
                                "name": "语法基础",
                                "description": "Python 基本语法",
                                "concepts": [
                                    {
                                        "concept_id": "c1",
                                        "name": "变量和数据类型",
                                        "description": "学习 Python 变量和数据类型",
                                        "estimated_hours": 3.0,
                                        "prerequisites": [],
                                        "difficulty": "easy",
                                        "keywords": ["变量", "数据类型"]
                                    },
                                    {
                                        "concept_id": "c2",
                                        "name": "控制流程",
                                        "description": "学习条件语句和循环",
                                        "estimated_hours": 4.0,
                                        "prerequisites": ["c1"],
                                        "difficulty": "easy",
                                        "keywords": ["if", "for", "while"]
                                    }
                                ]
                            }
                        ]
                    }
                ],
                "total_estimated_hours": 7.0,
                "recommended_completion_weeks": 2
            },
            "design_rationale": "根据用户零基础背景，从 Python 基础开始设计课程"
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = f"```json\n{json.dumps(response_data, ensure_ascii=False)}\n```"
        return response
    
    @pytest.mark.asyncio
    async def test_design_success(
        self,
        sample_intent_analysis,
        sample_learning_preferences,
        mock_llm_curriculum_response
    ):
        """测试成功设计课程"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_curriculum_response
            
            agent = CurriculumArchitectAgent()
            result = await agent.design(
                intent_analysis=sample_intent_analysis,
                user_preferences=sample_learning_preferences,
            )
            
            # 验证返回类型
            assert isinstance(result, CurriculumDesignOutput)
            assert isinstance(result.framework, RoadmapFramework)
            
            # 验证框架内容
            assert result.framework.roadmap_id == "roadmap-test-001"
            assert len(result.framework.stages) >= 1
            assert result.design_rationale is not None
    
    @pytest.mark.asyncio
    async def test_design_creates_valid_structure(
        self,
        sample_intent_analysis,
        sample_learning_preferences,
        mock_llm_curriculum_response
    ):
        """测试生成的结构有效"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_curriculum_response
            
            agent = CurriculumArchitectAgent()
            result = await agent.design(
                intent_analysis=sample_intent_analysis,
                user_preferences=sample_learning_preferences,
            )
            
            # 验证结构有效性
            assert result.framework.validate_structure() is True
    
    @pytest.mark.asyncio
    async def test_design_includes_prerequisites(
        self,
        sample_intent_analysis,
        sample_learning_preferences,
        mock_llm_curriculum_response
    ):
        """测试生成的课程包含前置关系"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_curriculum_response
            
            agent = CurriculumArchitectAgent()
            result = await agent.design(
                intent_analysis=sample_intent_analysis,
                user_preferences=sample_learning_preferences,
            )
            
            # 检查概念
            concepts = []
            for stage in result.framework.stages:
                for module in stage.modules:
                    concepts.extend(module.concepts)
            
            # 至少有一个概念有前置依赖
            has_prerequisites = any(len(c.prerequisites) > 0 for c in concepts)
            assert has_prerequisites or len(concepts) == 1  # 单个概念没有前置依赖也是合理的

