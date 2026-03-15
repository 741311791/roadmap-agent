"""
`RetryService` 的单元测试。
"""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.constants import TaskStatus, WorkflowStep
from app.schemas.retry import RetryMode, RetryRequest, RetryResponse, RetryScope
from app.services.workflows.generation.retry_service import RetryService


@pytest.mark.asyncio
async def test_resume_from_checkpoint_falls_back_to_content_generation_stage() -> None:
    """
    当主图 checkpoint 已无 next 节点，且任务停留在内容生成阶段时，
    应直接重发内容生成任务，而不是继续调用主图断点续传。
    """
    task_id = "task-content-retry"
    task = SimpleNamespace(
        task_id=task_id,
        roadmap_id="roadmap-123",
        user_id="user-123",
        status=TaskStatus.CANCELLED.value,
        current_step=WorkflowStep.CONTENT_GENERATION_QUEUED.value,
        content_generation_status="failed",
    )
    request = RetryRequest(mode=RetryMode.RESUME, reason="内容生成 Worker 中断后重试")

    state = SimpleNamespace(
        tasks=[],
        next=[],
        values={
            "roadmap_framework": MagicMock(),
            "intent_analysis": MagicMock(),
            "user_request": MagicMock(),
        },
    )

    mock_executor = MagicMock()
    mock_executor.graph.aget_state = AsyncMock(return_value=state)

    mock_factory = MagicMock()
    mock_factory.initialize = AsyncMock()
    mock_factory.create_workflow_executor.return_value = mock_executor

    expected_response = RetryResponse(
        success=True,
        message="内容生成重试已启动",
        task_id=task_id,
        celery_task_id="content-celery-123",
        retry_scope=RetryScope.STAGE,
        retry_from=WorkflowStep.CONTENT_GENERATION.value,
    )

    service = RetryService()

    with (
        patch(
            "app.services.workflows.generation.retry_service.OrchestratorFactory",
            return_value=mock_factory,
        ),
        patch.object(
            service,
            "_retry_content_generation_stage",
            new=AsyncMock(return_value=expected_response),
        ) as mock_retry_content_generation_stage,
        patch(
            "app.services.workflows.generation.retry_service.asyncio.to_thread",
            new=AsyncMock(side_effect=AssertionError("不应继续调主图 resume 任务")),
        ),
    ):
        result = await service._resume_from_checkpoint(
            task_id=task_id,
            task=task,
            request=request,
        )

    assert result == expected_response
    mock_retry_content_generation_stage.assert_awaited_once_with(
        task_id=task_id,
        task=task,
        state_values=state.values,
        reason=request.reason,
    )


@pytest.mark.asyncio
async def test_retry_content_generation_stage_returns_immediately_with_background_dispatch() -> None:
    """
    内容生成阶段重试应立即返回成功响应，并将实际 Celery 派发放到后台任务。
    """
    task_id = "task-background-dispatch"
    task = SimpleNamespace(
        task_id=task_id,
        roadmap_id="roadmap-456",
        user_id="user-456",
        status=TaskStatus.CANCELLED.value,
        current_step=WorkflowStep.CONTENT_GENERATION_QUEUED.value,
        content_generation_status="failed",
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session_context = AsyncMock()
    mock_session_context.__aenter__.return_value = mock_session
    mock_session_context.__aexit__.return_value = None

    mock_task_record = SimpleNamespace(
        status=TaskStatus.CANCELLED.value,
        current_step=WorkflowStep.CONTENT_GENERATION_QUEUED.value,
        content_generation_status="failed",
        error_message="Task cancelled by user",
        completed_at="2026-03-14T00:00:00Z",
    )
    mock_task_crud = MagicMock()
    mock_task_crud.get_by_task_id = AsyncMock(return_value=mock_task_record)

    service = RetryService()
    background_task = MagicMock()
    create_task_calls: list[str] = []

    def create_task_mock(coro, *, name=None):
        create_task_calls.append(name)
        coro.close()
        return background_task

    with (
        patch(
            "app.services.workflows.generation.retry_service.get_celery_session",
            return_value=mock_session_context,
        ),
        patch(
            "app.services.workflows.generation.retry_service.get_task_crud",
            return_value=mock_task_crud,
        ),
        patch(
            "app.services.workflows.generation.retry_service.notification_service.publish_progress",
            new=AsyncMock(),
        ) as mock_publish_progress,
        patch("app.services.workflows.generation.retry_service.asyncio.create_task", new=create_task_mock),
        patch.object(
            service,
            "_dispatch_content_generation_stage_in_background",
            new=AsyncMock(),
        ) as mock_background_dispatch,
    ):
        result = await service._retry_content_generation_stage(
            task_id=task_id,
            task=task,
            state_values={"roadmap_framework": MagicMock()},
            reason="前端手动重试",
        )

    assert result.success is True
    assert result.task_id == task_id
    assert result.celery_task_id is None
    assert result.retry_scope == RetryScope.STAGE
    assert result.retry_from == WorkflowStep.CONTENT_GENERATION.value

    assert mock_task_record.status == TaskStatus.PROCESSING.value
    assert mock_task_record.current_step == WorkflowStep.CONTENT_GENERATION_QUEUED.value
    assert mock_task_record.content_generation_status == "processing"
    assert mock_task_record.error_message is None
    assert mock_task_record.completed_at is None

    mock_task_crud.get_by_task_id.assert_awaited_once_with(mock_session, task_id)
    assert create_task_calls == [f"retry_content_generation_dispatch_{task_id}"]
    mock_publish_progress.assert_awaited_once()
    mock_background_dispatch.assert_called_once()
