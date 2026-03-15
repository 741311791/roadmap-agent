from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.orchestrator.subgraphs.content_generation_shared import generate_tutorial_for_concept
from app.models.domain import Concept, LearningPreferences, TutorialGenerationOutput


@pytest.mark.asyncio
async def test_generate_tutorial_for_concept_uses_execute_contract() -> None:
    """测试内容子图仍通过 execute 契约调用 TutorialGeneratorAgent"""

    concept = Concept(
        concept_id="concept-001",
        name="React Hooks",
        description="React 中的状态与副作用能力",
        estimated_hours=3.0,
        prerequisites=[],
        difficulty="medium",
        keywords=["hooks", "react"],
    )
    preferences = LearningPreferences(
        learning_goal="掌握 React 开发",
        available_hours_per_week=10,
        motivation="职业发展",
        current_level="intermediate",
        career_background="前端开发",
        content_preference=["text", "hands_on"],
        primary_language="zh",
    )
    tutorial_output = TutorialGenerationOutput(
        concept_id=concept.concept_id,
        tutorial_id="tutorial-001",
        title="React Hooks 教程",
        summary="讲解 React Hooks 的核心能力",
        content_url="roadmap-1/concepts/concept-001/v1.md",
        content_status="completed",
        content_version=1,
        estimated_completion_time=45,
    )

    tutorial_agent = MagicMock()
    tutorial_agent.execute = AsyncMock(return_value=tutorial_output)

    notification_service = SimpleNamespace(
        publish_concept_complete=AsyncMock(),
        publish_concept_failed=AsyncMock(),
    )
    runtime_context = SimpleNamespace(
        agent_factory=SimpleNamespace(create_tutorial_generator=lambda: tutorial_agent),
        notification_service=notification_service,
    )
    config = {"configurable": {"runtime_context": runtime_context}}
    state = {
        "concept": concept,
        "context": {"roadmap_id": "roadmap-1"},
        "user_preferences": preferences,
        "task_id": "task-001",
        "roadmap_id": "roadmap-1",
    }

    result = await generate_tutorial_for_concept(state, config)

    assert result["tutorials"] == [tutorial_output]
    tutorial_agent.execute.assert_awaited_once()
    notification_service.publish_concept_complete.assert_awaited_once()
    notification_service.publish_concept_failed.assert_not_awaited()
