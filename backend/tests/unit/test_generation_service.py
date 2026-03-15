"""
`GenerationService` 的单元测试。
"""
import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.constants import TaskStatus, WorkflowStep
from app.services.workflows.generation.generation_service import (
    DISPATCH_TIMEOUT_SECONDS,
    GenerationService,
)


def _build_user_request() -> SimpleNamespace:
    """
    构造最小可用的用户请求对象。

    Returns:
        用于测试的 UserRequest 替身对象
    """
    preferences = SimpleNamespace(
        learning_goal="掌握机器学习基础",
        model_dump=MagicMock(return_value={"preferred_language": "zh"}),
    )
    return SimpleNamespace(
        user_id="user-123",
        turbo_mode=True,
        preferences=preferences,
    )


@pytest.mark.asyncio
async def test_dispatch_task_in_background_marks_failure_on_timeout() -> None:
    """
    当 Celery publish 超时时，应走统一失败处理，而不是静默停留在 pending。
    """
    service = GenerationService()
    user_request = _build_user_request()
    fake_task_module = SimpleNamespace(generate_roadmap=SimpleNamespace(apply_async=MagicMock()))

    async def wait_for_timeout(awaitable, timeout):
        assert timeout == DISPATCH_TIMEOUT_SECONDS
        awaitable.close()
        raise asyncio.TimeoutError()

    with (
        patch.dict(sys.modules, {"app.tasks.roadmap_generation_tasks": fake_task_module}),
        patch(
            "app.services.workflows.generation.generation_service.asyncio.wait_for",
            new=AsyncMock(side_effect=wait_for_timeout),
        ),
        patch.object(
            service,
            "_mark_dispatch_failed",
            new=AsyncMock(),
        ) as mock_mark_dispatch_failed,
    ):
        await service._dispatch_task_in_background("task-timeout", user_request)

    mock_mark_dispatch_failed.assert_awaited_once()
    call_kwargs = mock_mark_dispatch_failed.await_args.kwargs
    assert call_kwargs["task_id"] == "task-timeout"
    assert call_kwargs["failure_reason"] == "timeout"
    assert "派发超时" in call_kwargs["error_message"]
    assert isinstance(call_kwargs["error"], asyncio.TimeoutError)


@pytest.mark.asyncio
async def test_mark_dispatch_failed_updates_task_status_and_notifies() -> None:
    """
    当后台派发明确失败时，应将任务标记为 failed，并发送失败通知。
    """
    service = GenerationService()
    user_request = _build_user_request()

    mock_task = SimpleNamespace(
        task_id="task-failed",
        celery_task_id=None,
        status=TaskStatus.PENDING.value,
        current_step=WorkflowStep.INIT.value,
    )
    mock_task_crud = MagicMock()
    mock_task_crud.get_by_task_id = AsyncMock(return_value=mock_task)
    mock_task_crud.update_task_status = AsyncMock(return_value=True)

    mock_session = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None

    error = RuntimeError("broker unavailable")

    with (
        patch(
            "app.services.workflows.generation.generation_service.async_session_maker.begin",
            return_value=mock_session_context,
        ),
        patch(
            "app.services.workflows.generation.generation_service.get_task_crud",
            return_value=mock_task_crud,
        ),
        patch(
            "app.services.workflows.generation.generation_service.notification_service.publish_failed",
            new=AsyncMock(),
        ) as mock_publish_failed,
    ):
        await service._mark_dispatch_failed(
            task_id="task-failed",
            user_request=user_request,
            error_message="Celery 任务派发失败：broker unavailable",
            error=error,
            failure_reason="exception",
        )

    mock_task_crud.get_by_task_id.assert_awaited_once_with(mock_session, "task-failed")
    mock_task_crud.update_task_status.assert_awaited_once_with(
        session=mock_session,
        task_id="task-failed",
        status=TaskStatus.FAILED.value,
        current_step=WorkflowStep.FAILED.value,
        error_message="Celery 任务派发失败：broker unavailable",
    )
    mock_publish_failed.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_dispatch_failed_skips_failed_update_when_celery_id_exists() -> None:
    """
    若任务已被其他链路成功写回 celery_task_id，不应再覆盖为 failed。
    """
    service = GenerationService()
    user_request = _build_user_request()

    mock_task = SimpleNamespace(
        task_id="task-race",
        celery_task_id="celery-123",
        status=TaskStatus.PENDING.value,
        current_step=WorkflowStep.INIT.value,
    )
    mock_task_crud = MagicMock()
    mock_task_crud.get_by_task_id = AsyncMock(return_value=mock_task)
    mock_task_crud.update_task_status = AsyncMock(return_value=True)

    mock_session = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None

    with (
        patch(
            "app.services.workflows.generation.generation_service.async_session_maker.begin",
            return_value=mock_session_context,
        ),
        patch(
            "app.services.workflows.generation.generation_service.get_task_crud",
            return_value=mock_task_crud,
        ),
        patch(
            "app.services.workflows.generation.generation_service.notification_service.publish_failed",
            new=AsyncMock(),
        ) as mock_publish_failed,
    ):
        await service._mark_dispatch_failed(
            task_id="task-race",
            user_request=user_request,
            error_message="Celery 任务派发超时",
            error=asyncio.TimeoutError(),
            failure_reason="timeout",
        )

    mock_task_crud.get_by_task_id.assert_awaited_once_with(mock_session, "task-race")
    mock_task_crud.update_task_status.assert_not_awaited()
    mock_publish_failed.assert_not_awaited()
