"""
A5: 资源推荐师 (ResourceRecommenderAgent) 集成测试
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from app.agents.resource_recommender import ResourceRecommenderAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    ResourceRecommendationInput,
    ResourceRecommendationOutput,
    Resource,
)


class TestResourceRecommenderAgent:
    """资源推荐师 Agent 集成测试"""
    
    @pytest.fixture
    def mock_llm_resource_response(self):
        """Mock LLM 返回的资源推荐结果"""
        response_data = {
            "concept_id": "c1",
            "resources": [
                {
                    "title": "MDN Web Docs - HTML 入门",
                    "url": "https://developer.mozilla.org/zh-CN/docs/Learn/HTML",
                    "type": "documentation",
                    "description": "Mozilla 官方的 HTML 入门教程，内容全面且权威。",
                    "relevance_score": 0.95
                },
                {
                    "title": "HTML 教程 - W3Schools",
                    "url": "https://www.w3schools.com/html/",
                    "type": "article",
                    "description": "互动式 HTML 学习教程，包含在线编辑器。",
                    "relevance_score": 0.90
                },
                {
                    "title": "HTML Crash Course For Absolute Beginners",
                    "url": "https://www.youtube.com/watch?v=UB1O30fR-EE",
                    "type": "video",
                    "description": "适合初学者的 HTML 速成视频课程。",
                    "relevance_score": 0.85
                }
            ],
            "search_queries_used": [
                "HTML 官方文档",
                "HTML 入门教程",
                "HTML 视频课程"
            ]
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = json.dumps(response_data, ensure_ascii=False)
        response.choices[0].message.tool_calls = None
        return response
    
    @pytest.fixture
    def mock_web_search_result(self):
        """Mock Web 搜索结果"""
        mock_result = MagicMock()
        mock_result.results = [
            {
                "title": "MDN Web Docs",
                "url": "https://developer.mozilla.org/",
                "snippet": "MDN Web Docs 提供有关开放网络技术的信息。"
            },
            {
                "title": "W3Schools HTML Tutorial",
                "url": "https://www.w3schools.com/html/",
                "snippet": "Well organized and easy to understand Web building tutorials."
            }
        ]
        mock_result.total_found = 2
        return mock_result
    
    @pytest.mark.asyncio
    async def test_recommend_success(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_resource_response,
    ):
        """测试成功推荐资源"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_resource_response
            
            agent = ResourceRecommenderAgent()
            
            context = {
                "roadmap_id": "roadmap-001",
                "stage_id": "s1",
                "stage_name": "前端基础",
                "module_id": "m1",
                "module_name": "Web 基础",
            }
            
            result = await agent.recommend(
                concept=sample_concept,
                context=context,
                user_preferences=sample_learning_preferences,
            )
            
            # 验证返回类型
            assert isinstance(result, ResourceRecommendationOutput)
            
            # 验证内容
            assert result.concept_id == sample_concept.concept_id
            assert len(result.resources) > 0
            assert all(isinstance(r, Resource) for r in result.resources)
    
    @pytest.mark.asyncio
    async def test_recommend_returns_multiple_resource_types(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_resource_response,
    ):
        """测试推荐的资源包含多种类型"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_resource_response
            
            agent = ResourceRecommenderAgent()
            
            result = await agent.recommend(
                concept=sample_concept,
                context={},
                user_preferences=sample_learning_preferences,
            )
            
            # 验证资源类型多样性
            resource_types = set(r.type for r in result.resources)
            assert len(resource_types) >= 2  # 至少有两种不同类型的资源
    
    @pytest.mark.asyncio
    async def test_recommend_resources_have_valid_scores(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_resource_response,
    ):
        """测试推荐的资源有有效的相关性评分"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_resource_response
            
            agent = ResourceRecommenderAgent()
            
            result = await agent.recommend(
                concept=sample_concept,
                context={},
                user_preferences=sample_learning_preferences,
            )
            
            # 验证相关性评分在有效范围内
            for resource in result.resources:
                assert 0 <= resource.relevance_score <= 1
    
    @pytest.mark.asyncio
    async def test_execute_interface(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_resource_response,
    ):
        """测试 execute 接口"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_resource_response
            
            agent = ResourceRecommenderAgent()
            
            input_data = ResourceRecommendationInput(
                concept=sample_concept,
                context={"roadmap_id": "roadmap-001"},
                user_preferences=sample_learning_preferences,
            )
            
            result = await agent.execute(input_data)
            
            assert isinstance(result, ResourceRecommendationOutput)
    
    @pytest.mark.asyncio
    async def test_recommend_with_tool_calls(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_web_search_result,
    ):
        """测试带工具调用的资源推荐"""
        # 创建带工具调用的响应
        tool_call_response = MagicMock()
        tool_call_response.choices = [MagicMock()]
        tool_call_response.choices[0].message.content = ""
        tool_call = MagicMock()
        tool_call.id = "call_123"
        tool_call.function.name = "web_search"
        tool_call.function.arguments = json.dumps({"query": "HTML 入门教程"})
        tool_call_response.choices[0].message.tool_calls = [tool_call]
        
        # 创建最终响应
        final_response_data = {
            "concept_id": "c1",
            "resources": [
                {
                    "title": "MDN Web Docs",
                    "url": "https://developer.mozilla.org/",
                    "type": "documentation",
                    "description": "官方文档",
                    "relevance_score": 0.95
                }
            ],
            "search_queries_used": ["HTML 入门教程"]
        }
        
        final_response = MagicMock()
        final_response.choices = [MagicMock()]
        final_response.choices[0].message.content = json.dumps(final_response_data, ensure_ascii=False)
        final_response.choices[0].message.tool_calls = None
        
        with patch("litellm.acompletion") as mock_completion, \
             patch("app.agents.resource_recommender.tool_registry") as mock_registry:
            
            # 设置 mock 返回序列：先返回工具调用，再返回最终结果
            mock_completion.side_effect = [tool_call_response, final_response]
            
            # Mock 搜索工具
            mock_search_tool = AsyncMock()
            mock_search_tool.execute.return_value = mock_web_search_result
            mock_registry.get.return_value = mock_search_tool
            
            agent = ResourceRecommenderAgent()
            
            result = await agent.recommend(
                concept=sample_concept,
                context={},
                user_preferences=sample_learning_preferences,
            )
            
            # 验证结果
            assert isinstance(result, ResourceRecommendationOutput)
            assert len(result.resources) > 0
            # 验证搜索查询被记录
            assert len(result.search_queries_used) > 0
    
    @pytest.mark.asyncio
    async def test_recommend_tracks_search_queries(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_resource_response,
    ):
        """测试搜索查询被正确追踪"""
        with patch("litellm.acompletion") as mock_completion:
            
            mock_completion.return_value = mock_llm_resource_response
            
            agent = ResourceRecommenderAgent()
            
            result = await agent.recommend(
                concept=sample_concept,
                context={},
                user_preferences=sample_learning_preferences,
            )
            
            # 验证搜索查询列表
            assert isinstance(result.search_queries_used, list)

