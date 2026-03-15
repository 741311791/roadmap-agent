"""
测试 RoadmapService 的任务状态查询逻辑。
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.roadmaps.roadmap_service import RoadmapService


@pytest.mark.asyncio
async def test_get_task_status_uses_database_current_step_only() -> None:
    """
    验证任务状态查询只使用数据库中的 current_step。

    该测试用于防止展示层再次从 checkpointer 覆盖数据库状态，
    从而导致 REST 与 WebSocket 初始状态不一致。
    """
    task = SimpleNamespace(
        task_id="task-123",
        status="processing",
        current_step="curriculum_design",
        roadmap_id="roadmap-123",
        created_at=None,
        updated_at=None,
        error_message=None,
        user_request={"turbo_mode": False},
    )

    mock_session = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None

    mock_task_crud = MagicMock()
    mock_task_crud.get_by_task_id = AsyncMock(return_value=task)
    mock_task_crud.get_creation_queue_info = AsyncMock(return_value=None)

    mock_orchestrator = MagicMock()
    mock_orchestrator.checkpointer = MagicMock()
    mock_orchestrator.checkpointer.aget_tuple = AsyncMock(
        side_effect=AssertionError("展示状态查询不应访问 checkpointer")
    )

    service = RoadmapService(mock_orchestrator)

    with (
        patch("app.services.roadmaps.roadmap_service.async_session_maker", return_value=mock_session_context),
        patch("app.services.roadmaps.roadmap_service.get_task_crud", return_value=mock_task_crud),
    ):
        result = await service.get_task_status("task-123")

    assert result is not None
    assert result.task_id == "task-123"
    assert result.status == "processing"
    assert result.current_step == "curriculum_design"
    assert result.roadmap_id == "roadmap-123"
    assert result.turbo_mode is False
    mock_orchestrator.checkpointer.aget_tuple.assert_not_called()


@pytest.mark.asyncio
async def test_get_task_status_turbo_mode_true() -> None:
    """
    验证 turbo_mode=True 时从 user_request JSON 正确回填到响应 Schema。
    """
    task = SimpleNamespace(
        task_id="task-456",
        status="processing",
        current_step="content_generation_queued",
        roadmap_id="roadmap-456",
        created_at=None,
        updated_at=None,
        error_message=None,
        user_request={"turbo_mode": True},
    )

    mock_session = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None

    mock_task_crud = MagicMock()
    mock_task_crud.get_by_task_id = AsyncMock(return_value=task)
    mock_task_crud.get_creation_queue_info = AsyncMock(return_value=None)

    service = RoadmapService(MagicMock())

    with (
        patch("app.services.roadmaps.roadmap_service.async_session_maker", return_value=mock_session_context),
        patch("app.services.roadmaps.roadmap_service.get_task_crud", return_value=mock_task_crud),
    ):
        result = await service.get_task_status("task-456")

    assert result is not None
    assert result.turbo_mode is True
    assert result.current_step == "content_generation_queued"
