"""
A1: 需求分析师 (IntentAnalyzerAgent) 集成测试
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from app.agents.intent_analyzer import IntentAnalyzerAgent
from app.models.domain import UserRequest, IntentAnalysisOutput


class TestIntentAnalyzerAgent:
    """需求分析师 Agent 集成测试"""
    
    @pytest.fixture
    def mock_llm_intent_response(self):
        """Mock LLM 返回的需求分析结果"""
        response_data = {
            "parsed_goal": "系统学习 Python 编程，从基础语法到 Web 开发",
            "key_technologies": ["Python", "Flask", "PostgreSQL", "Docker"],
            "difficulty_profile": "初学者，需要从基础开始，循序渐进",
            "time_constraint": "每周 10 小时，预计 3 个月完成基础学习",
            "recommended_focus": ["Python 基础", "Web 框架", "数据库操作"]
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = f"```json\n{json.dumps(response_data, ensure_ascii=False)}\n```"
        return response
    
    @pytest.mark.asyncio
    async def test_analyze_success(self, sample_user_request, mock_llm_intent_response):
        """测试成功分析用户需求"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_intent_response
            
            agent = IntentAnalyzerAgent()
            result = await agent.analyze(sample_user_request)
            
            # 验证返回类型
            assert isinstance(result, IntentAnalysisOutput)
            
            # 验证调用
            mock_completion.assert_called_once()
            
            # 验证结果内容
            assert "Python" in result.key_technologies
            assert len(result.recommended_focus) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_extracts_key_technologies(self, sample_user_request, mock_llm_intent_response):
        """测试能够提取关键技术栈"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_intent_response
            
            agent = IntentAnalyzerAgent()
            result = await agent.analyze(sample_user_request)
            
            assert len(result.key_technologies) >= 1
            assert all(isinstance(tech, str) for tech in result.key_technologies)
    
    @pytest.mark.asyncio
    async def test_analyze_handles_json_without_code_block(self, sample_user_request):
        """测试处理不带代码块的 JSON 响应"""
        response_data = {
            "parsed_goal": "学习编程",
            "key_technologies": ["Python"],
            "difficulty_profile": "初学者",
            "time_constraint": "3个月",
            "recommended_focus": ["基础语法"]
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = json.dumps(response_data, ensure_ascii=False)
        
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = response
            
            agent = IntentAnalyzerAgent()
            result = await agent.analyze(sample_user_request)
            
            assert result.parsed_goal == "学习编程"
    
    @pytest.mark.asyncio
    async def test_analyze_with_additional_context(self, sample_learning_preferences):
        """测试带额外上下文的分析"""
        request = UserRequest(
            user_id="test-user",
            session_id="test-session",
            preferences=sample_learning_preferences,
            additional_context="我有数学背景，对数据分析感兴趣",
        )
        
        response_data = {
            "parsed_goal": "学习数据分析",
            "key_technologies": ["Python", "Pandas", "NumPy"],
            "difficulty_profile": "有数学基础，可以直接学习数据分析",
            "time_constraint": "3个月",
            "recommended_focus": ["数据处理", "可视化"]
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = f"```json\n{json.dumps(response_data, ensure_ascii=False)}\n```"
        
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = response
            
            agent = IntentAnalyzerAgent()
            result = await agent.analyze(request)
            
            assert "数据分析" in result.parsed_goal

