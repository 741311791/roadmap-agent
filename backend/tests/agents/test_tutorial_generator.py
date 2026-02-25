import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.models.domain import (
    Concept, 
    LearningPreferences, 
    TutorialGenerationInput
)


@pytest.fixture
def mock_concept():
    """模拟概念数据"""
    return Concept(
        concept_id="test-001",
        name="React Hooks",
        description="React 16.8 引入的状态管理特性",
        difficulty="medium",  # 修复：使用 'easy', 'medium' 或 'hard'
        estimated_hours=3.0,
        prerequisites=["react-basics"],
        keywords=["useState", "useEffect", "hooks"],
    )


@pytest.fixture
def mock_user_preferences():
    """模拟用户偏好"""
    return LearningPreferences(
        learning_goal="掌握 React 开发",
        available_hours_per_week=10,
        motivation="职业发展",
        current_level="intermediate",
        career_background="前端开发 2 年经验",
        content_preference=["visual", "text", "hands_on"],
        primary_language="zh",
    )


@pytest.mark.asyncio
async def test_tutorial_generator_tools_loading():
    """测试工具加载"""
    agent = TutorialGeneratorAgent()
    tools = await agent._get_tools()
    
    assert len(tools) > 0
    tool_names = [t.name for t in tools]
    assert "web_search" in tool_names


@pytest.mark.asyncio
async def test_tutorial_generator_system_prompt(mock_concept, mock_user_preferences):
    """测试 System Prompt 生成"""
    agent = TutorialGeneratorAgent()
    
    prompt = agent._get_system_prompt(
        concept=mock_concept,
        context={"stage_name": "基础阶段"},
        user_preferences=mock_user_preferences,
    )
    
    assert "React Hooks" in prompt
    assert "resolve-library-id" in prompt
    assert "query-docs" in prompt
    assert "web_search" in prompt


@pytest.mark.asyncio
async def test_parse_output_two_part_format():
    """测试两段式输出解析"""
    agent = TutorialGeneratorAgent()
    
    mock_concept = Concept(
        concept_id="test-001",
        name="Test Concept",
        description="Test",
        difficulty="easy",  # 修复：使用 'easy', 'medium' 或 'hard'
        estimated_hours=1.0,
        prerequisites=[],
        keywords=[],
    )
    
    content = """
# React Hooks 教程

完整的教程内容...

===TUTORIAL_METADATA===
{
  "title": "React Hooks 原理",
  "summary": "深入讲解 React Hooks",
  "estimated_completion_time": 90
}
"""
    
    markdown, metadata = agent._parse_output(content, mock_concept)
    
    assert "React Hooks 教程" in markdown
    assert metadata["title"] == "React Hooks 原理"
    assert metadata["estimated_completion_time"] == 90


@pytest.mark.slow
@pytest.mark.asyncio
async def test_tutorial_generator_integration(mock_concept, mock_user_preferences):
    """集成测试：完整生成流程（需要真实 API Key）"""
    agent = TutorialGeneratorAgent()
    
    result = await agent.generate(
        concept=mock_concept,
        context={"roadmap_id": "test-roadmap", "stage_name": "基础"},
        user_preferences=mock_user_preferences,
    )
    
    assert result.concept_id == "test-001"
    assert result.content_url  # S3 Key
    assert result.content_status == "completed"

