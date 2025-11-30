"""
A2E: 路线图编辑师 (RoadmapEditorAgent) 集成测试
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from app.agents.roadmap_editor import RoadmapEditorAgent
from app.models.domain import (
    RoadmapFramework,
    ValidationIssue,
    LearningPreferences,
    RoadmapEditOutput,
)


class TestRoadmapEditorAgent:
    """路线图编辑师 Agent 集成测试"""
    
    @pytest.fixture
    def mock_llm_edit_response(self, sample_roadmap_framework):
        """Mock LLM 返回的编辑结果"""
        # 使用 sample_roadmap_framework 的结构，但做些修改
        framework_dict = sample_roadmap_framework.model_dump()
        framework_dict["title"] = "修改后的学习路线"
        
        response_data = {
            "framework": framework_dict,
            "modification_summary": "根据验证反馈，调整了概念的前置关系",
            "preserved_elements": ["保留了 Stage 1 的整体结构", "保留了所有核心概念"]
        }
        
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = f"```json\n{json.dumps(response_data, ensure_ascii=False)}\n```"
        return response
    
    @pytest.mark.asyncio
    async def test_edit_success(
        self,
        sample_roadmap_framework,
        sample_validation_output_invalid,
        sample_learning_preferences,
        mock_llm_edit_response
    ):
        """测试成功编辑路线图"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_edit_response
            
            agent = RoadmapEditorAgent()
            result = await agent.edit(
                existing_framework=sample_roadmap_framework,
                validation_issues=sample_validation_output_invalid.issues,
                user_preferences=sample_learning_preferences,
                modification_count=0,
            )
            
            # 验证返回类型
            assert isinstance(result, RoadmapEditOutput)
            assert isinstance(result.framework, RoadmapFramework)
            
            # 验证修改说明
            assert result.modification_summary is not None
            assert len(result.modification_summary) > 0
    
    @pytest.mark.asyncio
    async def test_edit_preserves_roadmap_id(
        self,
        sample_roadmap_framework,
        sample_validation_output_invalid,
        sample_learning_preferences,
        mock_llm_edit_response
    ):
        """测试编辑后保留路线图 ID"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_edit_response
            
            agent = RoadmapEditorAgent()
            result = await agent.edit(
                existing_framework=sample_roadmap_framework,
                validation_issues=sample_validation_output_invalid.issues,
                user_preferences=sample_learning_preferences,
                modification_count=0,
            )
            
            # 路线图 ID 应该保持不变
            assert result.framework.roadmap_id == sample_roadmap_framework.roadmap_id
    
    @pytest.mark.asyncio
    async def test_edit_with_multiple_issues(
        self,
        sample_roadmap_framework,
        sample_learning_preferences,
        mock_llm_edit_response
    ):
        """测试处理多个验证问题"""
        issues = [
            ValidationIssue(
                severity="critical",
                location="Stage 1 > Module 1",
                issue="问题1",
                suggestion="建议1",
            ),
            ValidationIssue(
                severity="warning",
                location="Stage 1 > Module 2",
                issue="问题2",
                suggestion="建议2",
            ),
            ValidationIssue(
                severity="suggestion",
                location="Stage 2",
                issue="问题3",
                suggestion="建议3",
            ),
        ]
        
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_edit_response
            
            agent = RoadmapEditorAgent()
            result = await agent.edit(
                existing_framework=sample_roadmap_framework,
                validation_issues=issues,
                user_preferences=sample_learning_preferences,
                modification_count=1,
            )
            
            assert isinstance(result, RoadmapEditOutput)
    
    @pytest.mark.asyncio
    async def test_edit_increments_modification_context(
        self,
        sample_roadmap_framework,
        sample_validation_output_invalid,
        sample_learning_preferences,
        mock_llm_edit_response
    ):
        """测试修改计数上下文"""
        with patch("litellm.acompletion") as mock_completion:
            mock_completion.return_value = mock_llm_edit_response
            
            agent = RoadmapEditorAgent()
            
            # 第一次修改
            await agent.edit(
                existing_framework=sample_roadmap_framework,
                validation_issues=sample_validation_output_invalid.issues,
                user_preferences=sample_learning_preferences,
                modification_count=0,
            )
            
            # 第二次修改
            await agent.edit(
                existing_framework=sample_roadmap_framework,
                validation_issues=sample_validation_output_invalid.issues,
                user_preferences=sample_learning_preferences,
                modification_count=1,
            )
            
            # 验证调用了两次
            assert mock_completion.call_count == 2

