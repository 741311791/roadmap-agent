from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.database import User, UserFeedback
from app.schemas.feedback import (
    FeedbackCategory,
    FeedbackContextType,
    UserFeedbackCreatePayload,
)
from app.services.shared.linear_feedback_service import LinearFeedbackService


@pytest.mark.asyncio
async def test_submit_feedback_creates_linear_issue_and_marks_local_record(monkeypatch) -> None:
    """提交通道成功时，应创建 Linear Issue 并回写本地记录。"""
    mock_crud = SimpleNamespace(
        create_feedback=AsyncMock(
            return_value=UserFeedback(
                feedback_id="feedback-1",
                user_id="user-1",
                username_snapshot="Alice",
                email_snapshot="alice@example.com",
                category="improvement",
                rating=5,
                summary="Great roadmap",
                details="The roadmap is useful and clear.",
                page_url="http://localhost:3000/roadmap/roadmap-1",
                context_type="generation_completed",
            )
        ),
        mark_submitted=AsyncMock(),
        mark_failed=AsyncMock(),
    )
    service = LinearFeedbackService(user_feedback_crud=mock_crud)

    graphql_mock = AsyncMock(
        side_effect=[
            {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue-1",
                        "identifier": "LIN-123",
                    },
                }
            },
            {
                "attachmentCreate": {
                    "success": True,
                    "attachment": {
                        "id": "attachment-1",
                    },
                }
            },
        ]
    )
    monkeypatch.setattr(service, "_execute_graphql", graphql_mock)

    monkeypatch.setattr("app.services.shared.linear_feedback_service.settings.LINEAR_API_KEY", "linear-key")
    monkeypatch.setattr("app.services.shared.linear_feedback_service.settings.LINEAR_TEAM_ID", "team-1")
    monkeypatch.setattr("app.services.shared.linear_feedback_service.settings.LINEAR_PROJECT_ID", "project-1")
    monkeypatch.setattr(
        "app.services.shared.linear_feedback_service.settings.LINEAR_LABEL_USER_FEEDBACK",
        "label-feedback",
    )
    monkeypatch.setattr(
        "app.services.shared.linear_feedback_service.settings.LINEAR_LABEL_IMPROVEMENT",
        "label-improvement",
    )
    monkeypatch.setattr("app.services.shared.linear_feedback_service.settings.LINEAR_WORKSPACE_URL", None)

    user = User(
        id="user-1",
        email="alice@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        username="Alice",
    )
    payload = UserFeedbackCreatePayload(
        rating=5,
        category=FeedbackCategory.IMPROVEMENT,
        summary="Great roadmap",
        details="The roadmap is useful and clear.",
        page_url="http://localhost:3000/roadmap/roadmap-1",
        context_type=FeedbackContextType.GENERATION_COMPLETED,
        roadmap_id="roadmap-1",
        task_id="task-1",
    )

    result = await service.submit_feedback(
        AsyncMock(),
        user=user,
        payload=payload,
    )

    assert result.feedback_id == "feedback-1"
    assert result.linear_issue_id == "issue-1"
    assert result.linear_issue_identifier == "LIN-123"
    assert result.linear_issue_url is None
    mock_crud.mark_submitted.assert_awaited_once()
    mock_crud.mark_failed.assert_not_called()
    assert graphql_mock.await_count == 2


@pytest.mark.asyncio
async def test_submit_feedback_without_project_id_only_uses_team_scope(monkeypatch) -> None:
    """未配置 Project 时，应只按 Team 创建反馈 issue。"""
    mock_crud = SimpleNamespace(
        create_feedback=AsyncMock(
            return_value=UserFeedback(
                feedback_id="feedback-2",
                user_id="user-2",
                username_snapshot="Bob",
                email_snapshot="bob@example.com",
                category="bug",
                rating=3,
                summary="Broken step",
                details="The page crashed after clicking complete.",
                page_url="http://localhost:3000/roadmap/roadmap-2",
                context_type="concept_completed",
            )
        ),
        mark_submitted=AsyncMock(),
        mark_failed=AsyncMock(),
    )
    service = LinearFeedbackService(user_feedback_crud=mock_crud)

    graphql_mock = AsyncMock(
        side_effect=[
            {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue-2",
                        "identifier": "LIN-456",
                    },
                }
            },
            {
                "attachmentCreate": {
                    "success": True,
                    "attachment": {
                        "id": "attachment-2",
                    },
                }
            },
        ]
    )
    monkeypatch.setattr(service, "_execute_graphql", graphql_mock)

    monkeypatch.setattr("app.services.shared.linear_feedback_service.settings.LINEAR_API_KEY", "linear-key")
    monkeypatch.setattr("app.services.shared.linear_feedback_service.settings.LINEAR_TEAM_ID", "team-1")
    monkeypatch.setattr("app.services.shared.linear_feedback_service.settings.LINEAR_PROJECT_ID", None)
    monkeypatch.setattr(
        "app.services.shared.linear_feedback_service.settings.LINEAR_LABEL_USER_FEEDBACK",
        "label-feedback",
    )
    monkeypatch.setattr(
        "app.services.shared.linear_feedback_service.settings.LINEAR_LABEL_BUG",
        "label-bug",
    )
    monkeypatch.setattr("app.services.shared.linear_feedback_service.settings.LINEAR_WORKSPACE_URL", None)

    user = User(
        id="user-2",
        email="bob@example.com",
        hashed_password="hashed",
        is_active=True,
        is_superuser=False,
        is_verified=True,
        username="Bob",
    )
    payload = UserFeedbackCreatePayload(
        rating=3,
        category=FeedbackCategory.BUG,
        summary="Broken step",
        details="The page crashed after clicking complete.",
        page_url="http://localhost:3000/roadmap/roadmap-2",
        context_type=FeedbackContextType.CONCEPT_COMPLETED,
        roadmap_id="roadmap-2",
        concept_id="concept-2",
    )

    await service.submit_feedback(
        AsyncMock(),
        user=user,
        payload=payload,
    )

    issue_call = graphql_mock.await_args_list[0]
    issue_input = issue_call.kwargs["variables"]["input"]

    assert issue_input["teamId"] == "team-1"
    assert "projectId" not in issue_input


def test_build_label_ids_returns_feedback_and_category_labels(monkeypatch) -> None:
    """标签映射应同时包含主标签与分类标签。"""
    service = LinearFeedbackService()

    monkeypatch.setattr("app.services.shared.linear_feedback_service.settings.LINEAR_LABEL_USER_FEEDBACK", "label-feedback")
    monkeypatch.setattr("app.services.shared.linear_feedback_service.settings.LINEAR_LABEL_BUG", "label-bug")

    label_ids = service._build_label_ids(FeedbackCategory.BUG)

    assert label_ids == ["label-feedback", "label-bug"]
