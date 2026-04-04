"""独立 Deer-Flow 实验室：上下文与上游 metadata 单元测试。"""

from types import SimpleNamespace

import pytest

from app.models.database import RoadmapChatThread, beijing_now
from app.schemas.deerflow_standalone import (
    DeerFlowStandaloneChatRequest,
    DeerFlowStandaloneChatContext,
    DeerFlowStandaloneThreadCreateRequest,
)
from app.services.learning.deerflow_context_service import DeerFlowContextService
from app.services.learning.deerflow_proxy_service import DeerFlowProxyService


@pytest.mark.asyncio
async def test_prepare_standalone_chat_payload_plain_upstream_and_metadata() -> None:
    """独立模式应上行用户原文，metadata 仅含 user_id 与 source，不得注入学习标签。"""

    svc = DeerFlowContextService()
    db = SimpleNamespace()
    user = SimpleNamespace(id="user-standalone-1")
    request = DeerFlowStandaloneChatRequest(
        message="  hello deer  ",
        context=DeerFlowStandaloneChatContext(mode="pro", reasoning_effort="medium"),
    )
    prepared = await svc.prepare_standalone_chat_payload(db, current_user=user, request=request)

    assert prepared.upstream_message == "hello deer"
    assert prepared.preview_text == "hello deer"
    assert "<learning_context>" not in prepared.upstream_message
    assert prepared.metadata == {
        "user_id": "user-standalone-1",
        "source": "deerflow_standalone",
    }
    assert prepared.runtime_context.get("mode") == "pro"
    assert prepared.runtime_context.get("is_plan_mode") is True


def test_prepare_standalone_thread_title_default() -> None:
    """无标题时应回退为 New Chat。"""

    title = DeerFlowContextService.prepare_standalone_thread_title(
        request=DeerFlowStandaloneThreadCreateRequest(title=None)
    )
    assert title == "New Chat"


def test_upstream_metadata_from_thread_standalone_vs_roadmap() -> None:
    """roadmap_id 为空时上游 metadata 应精简为实验室来源。"""

    standalone = RoadmapChatThread(
        thread_id="t1",
        user_id="u1",
        roadmap_id=None,
        created_at=beijing_now(),
        updated_at=beijing_now(),
    )
    assert DeerFlowProxyService._upstream_metadata_from_thread(standalone) == {
        "user_id": "u1",
        "source": "deerflow_standalone",
    }

    roadmap = RoadmapChatThread(
        thread_id="t2",
        user_id="u1",
        roadmap_id="r1",
        stage_id="s1",
        task_id=None,
        concept_id="c1",
        created_at=beijing_now(),
        updated_at=beijing_now(),
    )
    md = DeerFlowProxyService._upstream_metadata_from_thread(roadmap)
    assert md["source"] == "roadmap_agent"
    assert md["roadmap_id"] == "r1"
    assert md["concept_id"] == "c1"
