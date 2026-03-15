"""
测试创建类任务排队统计与陈旧 pending 清理逻辑。
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.crud.crud_task import TaskCRUD
from app.models.database import RoadmapTask
from app.services.workflows.generation.stale_pending_task_cleanup_service import (
    StalePendingTaskCleanupService,
)


def test_build_creation_queue_info_map_excludes_stale_init_pending_tasks() -> None:
    """
    验证排队统计会忽略长期停留在 init 的陈旧 pending 任务。
    """
    task_crud = TaskCRUD(RoadmapTask)
    now = datetime(2026, 3, 14, 16, 30, 0)

    stale_task = SimpleNamespace(
        task_id="stale-task",
        status="pending",
        task_type="creation",
        current_step="init",
        created_at=datetime(2026, 3, 14, 8, 0, 0),
    )
    fresh_task = SimpleNamespace(
        task_id="fresh-task",
        status="pending",
        task_type="creation",
        current_step="init",
        created_at=datetime(2026, 3, 14, 15, 50, 0),
    )
    queued_task = SimpleNamespace(
        task_id="queued-task",
        status="pending",
        task_type="creation",
        current_step="queued",
        created_at=datetime(2026, 3, 14, 15, 55, 0),
    )

    queue_info_map = task_crud.build_creation_queue_info_map(
        [stale_task, fresh_task, queued_task],
        now=now,
    )

    assert "stale-task" not in queue_info_map
    assert queue_info_map["fresh-task"] == {
        "queue_ahead_count": 0,
        "queue_position": 1,
    }
    assert queue_info_map["queued-task"] == {
        "queue_ahead_count": 1,
        "queue_position": 2,
    }


@pytest.mark.asyncio
async def test_cleanup_stale_pending_tasks_marks_tasks_failed() -> None:
    """
    验证启动清理会将陈旧 pending 创建任务标记为 failed。
    """
    stale_task = SimpleNamespace(
        task_id="stale-task",
        created_at=datetime(2026, 3, 4, 23, 1, 21),
        celery_task_id="celery-task-1",
    )

    mock_session = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None

    mock_task_crud = MagicMock()
    mock_task_crud.find_stale_pending_creation_tasks = AsyncMock(return_value=[stale_task])
    mock_task_crud.update_task_status = AsyncMock(return_value=True)

    service = StalePendingTaskCleanupService(stale_after_hours=6)

    with (
        patch(
            "app.services.workflows.generation.stale_pending_task_cleanup_service.async_session_maker.begin",
            return_value=mock_session_context,
        ),
        patch(
            "app.services.workflows.generation.stale_pending_task_cleanup_service.get_task_crud",
            return_value=mock_task_crud,
        ),
    ):
        result = await service.cleanup_stale_pending_tasks()

    assert result.total_found == 1
    assert result.cleaned == 1
    assert result.failed == 0
    mock_task_crud.update_task_status.assert_awaited_once()
    _, kwargs = mock_task_crud.update_task_status.await_args
    assert kwargs["task_id"] == "stale-task"
    assert kwargs["status"] == "failed"
    assert kwargs["current_step"] == "stale_pending_cleaned"
