"""
A4: 教程生成器 (TutorialGeneratorAgent) 集成测试
"""
import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock

from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    TutorialGenerationInput,
    TutorialGenerationOutput,
)


class TestTutorialGeneratorAgent:
    """教程生成器 Agent 集成测试"""
    
    @pytest.fixture
    def mock_llm_tutorial_response(self):
        """Mock LLM 返回的教程生成结果"""
        # 使用简单的教程内容，避免嵌套代码块导致 JSON 解析问题
        response_data = {
            "tutorial_id": "tutorial-test-001",
            "title": "HTML 基础入门教程",
            "summary": "本教程将带你从零开始学习 HTML，包括文档结构、常用标签和语义化实践。",
            "tutorial_content": "# HTML 基础入门\n\n## 1. 什么是 HTML\n\nHTML 是构建网页的基础标记语言。\n\n## 2. 总结\n\nHTML 是 Web 开发的基石。",
            "estimated_completion_time": 45
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = json.dumps(response_data, ensure_ascii=False)
        return response
    
    @pytest.fixture
    def mock_s3_upload(self):
        """Mock S3 上传"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.url = "s3://roadmap-content/tutorials/c1/v1.md"
        mock_result.key = "tutorials/c1/v1.md"
        mock_result.size_bytes = 2048
        return mock_result
    
    @pytest.mark.asyncio
    async def test_generate_success(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_tutorial_response,
        mock_s3_upload
    ):
        """测试成功生成教程"""
        with patch("litellm.acompletion") as mock_completion, \
             patch("app.core.tool_registry.tool_registry") as mock_registry:
            
            mock_completion.return_value = mock_llm_tutorial_response
            
            # Mock S3 Tool
            mock_s3_tool = AsyncMock()
            mock_s3_tool.execute.return_value = mock_s3_upload
            mock_registry.get.return_value = mock_s3_tool
            
            agent = TutorialGeneratorAgent()
            
            context = {
                "roadmap_id": "roadmap-001",
                "stage_id": "s1",
                "stage_name": "前端基础",
                "module_id": "m1",
                "module_name": "Web 基础",
            }
            
            result = await agent.generate(
                concept=sample_concept,
                context=context,
                user_preferences=sample_learning_preferences,
            )
            
            # 验证返回类型
            assert isinstance(result, TutorialGenerationOutput)
            
            # 验证内容
            assert result.concept_id == sample_concept.concept_id
            assert result.content_url is not None
            assert result.content_status == "completed"
    
    @pytest.mark.asyncio
    async def test_generate_returns_content_url(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_tutorial_response,
        mock_s3_upload
    ):
        """测试生成的教程包含 content_url"""
        with patch("litellm.acompletion") as mock_completion, \
             patch("app.agents.tutorial_generator.tool_registry") as mock_registry:
            
            mock_completion.return_value = mock_llm_tutorial_response
            
            # Mock S3 Tool
            mock_s3_tool = AsyncMock()
            mock_s3_tool.execute.return_value = mock_s3_upload
            mock_registry.get.return_value = mock_s3_tool
            
            agent = TutorialGeneratorAgent()
            
            context = {"roadmap_id": "roadmap-001"}
            
            result = await agent.generate(
                concept=sample_concept,
                context=context,
                user_preferences=sample_learning_preferences,
            )
            
            # 验证返回包含 content_url
            assert result.content_url is not None
            assert len(result.content_url) > 0
    
    @pytest.mark.asyncio
    async def test_execute_interface(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_tutorial_response,
        mock_s3_upload
    ):
        """测试 execute 接口"""
        with patch("litellm.acompletion") as mock_completion, \
             patch("app.core.tool_registry.tool_registry") as mock_registry:
            
            mock_completion.return_value = mock_llm_tutorial_response
            
            mock_s3_tool = AsyncMock()
            mock_s3_tool.execute.return_value = mock_s3_upload
            mock_registry.get.return_value = mock_s3_tool
            
            agent = TutorialGeneratorAgent()
            
            input_data = TutorialGenerationInput(
                concept=sample_concept,
                context={"roadmap_id": "roadmap-001"},
                user_preferences=sample_learning_preferences,
            )
            
            result = await agent.execute(input_data)
            
            assert isinstance(result, TutorialGenerationOutput)
    
    @pytest.mark.asyncio
    async def test_generate_includes_summary(
        self,
        sample_concept,
        sample_learning_preferences,
        mock_llm_tutorial_response,
        mock_s3_upload
    ):
        """测试生成的教程包含摘要"""
        with patch("litellm.acompletion") as mock_completion, \
             patch("app.core.tool_registry.tool_registry") as mock_registry:
            
            mock_completion.return_value = mock_llm_tutorial_response
            
            mock_s3_tool = AsyncMock()
            mock_s3_tool.execute.return_value = mock_s3_upload
            mock_registry.get.return_value = mock_s3_tool
            
            agent = TutorialGeneratorAgent()
            
            result = await agent.generate(
                concept=sample_concept,
                context={"roadmap_id": "roadmap-001"},
                user_preferences=sample_learning_preferences,
            )
            
            assert result.summary is not None
            assert len(result.summary) > 0
            assert len(result.summary) <= 500  # 摘要长度限制

