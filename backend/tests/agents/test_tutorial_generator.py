from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.factory import AgentFactory
from app.agents.tutorial_generator import (
    TutorialDraft,
    TutorialGeneratorAgent,
    TutorialMetadataDraft,
    TutorialResearchNotes,
)
from app.models.domain import Concept, LearningPreferences, TutorialGenerationInput


@pytest.fixture
def mock_concept() -> Concept:
    """模拟开发场景概念"""

    return Concept(
        concept_id="test-001",
        name="React Hooks",
        description="React 18 中常用的状态管理能力",
        difficulty="medium",
        estimated_hours=3.0,
        prerequisites=["react-basics"],
        keywords=["useState", "useEffect", "hooks"],
    )


@pytest.fixture
def hard_concept() -> Concept:
    """模拟需要研究的高复杂度概念"""

    return Concept(
        concept_id="test-002",
        name="LangGraph State Management",
        description="结合 LangGraph、checkpoint 与状态恢复的高级用法",
        difficulty="hard",
        estimated_hours=6.0,
        prerequisites=["c-1", "c-2", "c-3", "c-4"],
        keywords=["langgraph", "state", "checkpoint", "api"],
    )


@pytest.fixture
def lifestyle_concept() -> Concept:
    """模拟非开发场景概念"""

    return Concept(
        concept_id="life-001",
        name="法式烘焙入门",
        description="学习基础面团、发酵和烘焙技巧",
        difficulty="easy",
        estimated_hours=2.0,
        prerequisites=[],
        keywords=["烘焙", "面团", "发酵"],
    )


@pytest.fixture
def mock_user_preferences() -> LearningPreferences:
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


def test_rule_based_scenario_detection(
    mock_concept: Concept,
    lifestyle_concept: Concept,
) -> None:
    """测试本地规则的场景判定"""

    agent = TutorialGeneratorAgent()

    assert agent._is_development_scenario(mock_concept, {}) is True
    assert agent._is_development_scenario(lifestyle_concept, {}) is False


@pytest.mark.asyncio
async def test_research_stage_skipped_without_official_docs(
    lifestyle_concept: Concept,
    mock_user_preferences: LearningPreferences,
) -> None:
    """测试非开发场景会跳过研究阶段"""

    agent = TutorialGeneratorAgent()
    agent._call_llm = AsyncMock()

    notes = await agent._run_research_stage(
        concept=lifestyle_concept,
        context={},
        user_preferences=mock_user_preferences,
    )

    assert notes.scenario == "non_development"
    assert notes.used_official_docs is False
    assert notes.tool_budget == 0
    agent._call_llm.assert_not_awaited()


@pytest.mark.asyncio
async def test_research_stage_uses_budgeted_react(
    hard_concept: Concept,
    mock_user_preferences: LearningPreferences,
) -> None:
    """测试研究阶段会使用受预算约束的 ReAct 调用"""

    agent = TutorialGeneratorAgent()
    fake_response = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=(
                        "Overview:\n- 使用了官方文档确认状态恢复逻辑\n\n"
                        "VersionNotes:\n- 无\n\n"
                        "ExampleConstraints:\n- 示例中保持 StateGraph 用法一致\n\n"
                        "Pitfalls:\n- 避免混淆运行态和持久化状态\n\n"
                        "SourceSummary:\n- 已参考官方文档中的状态管理说明"
                    )
                )
            )
        ]
    )
    agent._get_tools = AsyncMock(
        return_value=[
            {
                "type": "function",
                "function": {
                    "name": "resolve-library-id",
                    "description": "resolve",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ]
    )
    agent._call_llm = AsyncMock(return_value=fake_response)

    notes = await agent._run_research_stage(
        concept=hard_concept,
        context={},
        user_preferences=mock_user_preferences,
    )

    assert notes.used_official_docs is True
    assert notes.tool_budget == 3
    assert "官方文档" in notes.research_summary
    assert agent._call_llm.await_args.kwargs["use_react"] is True
    assert agent._call_llm.await_args.kwargs["max_iterations"] == 3


@pytest.mark.asyncio
async def test_structured_write_falls_back_to_two_stage(
    mock_concept: Concept,
    mock_user_preferences: LearningPreferences,
) -> None:
    """测试结构化写作失败时会降级到 two-stage"""

    agent = TutorialGeneratorAgent()
    expected_draft = TutorialDraft(
        markdown_content="# React Hooks 教程\n\n## 概述\n内容",
        metadata=TutorialMetadataDraft(
            title="React Hooks 教程",
            summary="讲解 React Hooks 的核心用法",
            estimated_completion_time=45,
        ),
    )
    agent._call_llm = AsyncMock(side_effect=[RuntimeError("parse failed"), expected_draft])

    draft = await agent._write_tutorial_draft(
        concept=mock_concept,
        context={"roadmap_id": "roadmap-1"},
        user_preferences=mock_user_preferences,
        research_notes=TutorialResearchNotes(
            scenario="development",
            used_official_docs=False,
            tool_budget=0,
            research_summary="未进入官方文档研究阶段。",
        ),
    )

    assert draft == expected_draft
    assert agent._call_llm.await_args_list[0].kwargs["use_two_stage"] is False
    assert agent._call_llm.await_args_list[1].kwargs["use_two_stage"] is True


@pytest.mark.asyncio
async def test_generate_returns_expected_output(
    mock_concept: Concept,
    mock_user_preferences: LearningPreferences,
) -> None:
    """测试完整生成流程会返回 TutorialGenerationOutput"""

    agent = TutorialGeneratorAgent()
    agent._run_research_stage = AsyncMock(
        return_value=TutorialResearchNotes(
            scenario="development",
            used_official_docs=True,
            tool_budget=2,
            trigger_reasons=["概念与具体框架或 API 细节强相关"],
            research_summary="已参考官方文档。",
        )
    )
    agent._write_tutorial_draft = AsyncMock(
        return_value=TutorialDraft(
            markdown_content="# React Hooks 教程\n\n## 概述\n内容",
            metadata=TutorialMetadataDraft(
                title="React Hooks 教程",
                summary="讲解 React Hooks 的核心用法",
                estimated_completion_time=45,
            ),
        )
    )
    agent._upload_to_s3 = AsyncMock(return_value="roadmap-1/concepts/test-001/v1.md")

    result = await agent.execute(
        TutorialGenerationInput(
            concept=mock_concept,
            context={"roadmap_id": "roadmap-1", "content_version": 1},
            user_preferences=mock_user_preferences,
        )
    )

    assert result.concept_id == "test-001"
    assert result.title == "React Hooks 教程"
    assert result.content_url == "roadmap-1/concepts/test-001/v1.md"
    assert result.content_status == "completed"
    assert result.estimated_completion_time == 45


def test_agent_factory_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    """测试工厂仍正确注入 TutorialGeneratorAgent 配置"""

    monkeypatch.setattr(AgentFactory, "_register_default_tools", lambda self: None)
    settings = SimpleNamespace(
        GENERATOR_PROVIDER="test-provider",
        GENERATOR_MODEL="test-model",
        GENERATOR_BASE_URL="https://example.com",
        GENERATOR_API_KEY="test-key",
    )

    factory = AgentFactory(settings)
    agent = factory.create_tutorial_generator()

    assert agent.model_provider == "test-provider"
    assert agent.model_name == "test-model"
    assert agent.base_url == "https://example.com"
    assert agent.api_key == "test-key"

