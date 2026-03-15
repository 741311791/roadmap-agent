"""
单 Concept 内容生成耗时单元测试
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.orchestrator.subgraphs.single_concept_content_generation import fan_in_and_save
from app.models.domain import Concept
from app.schemas.handler_io import ConceptContentSaveResult


@pytest.mark.asyncio
async def test_fan_in_and_save_should_write_content_duration_ms():
    """
    测试保存 Concept 内容时应写入总耗时

    Returns:
        None
    """
    runtime_context = MagicMock()
    runtime_context.execution_logger = MagicMock()
    runtime_context.execution_logger.info = AsyncMock()
    runtime_context.notification_service = MagicMock()
    runtime_context.notification_service.publish_concept_all_content_complete = AsyncMock()

    config = {
        "configurable": {
            "runtime_context": runtime_context,
        }
    }

    state = {
        "concept": Concept(
            concept_id="roadmap-1:c-1-1-1",
            name="TypeScript 核心类型系统",
            description="测试概念",
            estimated_hours=2.0,
            prerequisites=[],
            difficulty="medium",
            keywords=[],
        ),
        "roadmap_id": "roadmap-1",
        "task_id": "task-1",
        "tutorial": None,
        "resource": None,
        "quiz": None,
        "errors": [],
        "concept_started_at": 100.0,
    }

    @asynccontextmanager
    async def mock_celery_session():
        yield object()

    save_result = ConceptContentSaveResult(
        concept_id="roadmap-1:c-1-1-1",
        tutorial="success",
        tutorial_output=None,
        resource="success",
        resource_output=None,
        quiz="success",
        quiz_output=None,
        metadata_saved=True,
    )

    with (
        patch("app.db.celery_session.get_celery_session", mock_celery_session),
        patch(
            "app.core.orchestrator.subgraphs.single_concept_content_generation.ConceptContentHandler.save_concept_content",
            new=AsyncMock(return_value=save_result),
        ),
        patch(
            "app.core.orchestrator.subgraphs.single_concept_content_generation.time.perf_counter",
            return_value=112.345,
        ),
    ):
        await fan_in_and_save(state, config)

    runtime_context.execution_logger.info.assert_awaited_once()
    _, kwargs = runtime_context.execution_logger.info.await_args
    assert kwargs["category"] == "content"
    assert kwargs["duration_ms"] >= 12344
