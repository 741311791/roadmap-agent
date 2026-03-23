from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from openai import AuthenticationError, BadRequestError

from app.schemas.mentor import MentorChatContext, MentorChatRequest
from app.services.learning.mentor_service import MentorService


class _FakeSessionContext:
    """模拟 async_session_maker.begin() 返回的异步上下文。"""

    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeSessionMaker:
    """模拟 async_session_maker，仅提供 begin()。"""

    def __init__(self, session: object) -> None:
        self._session = session

    def begin(self) -> _FakeSessionContext:
        return _FakeSessionContext(self._session)


@pytest.mark.asyncio
async def test_persist_chat_round_writes_messages_and_updates_session(monkeypatch) -> None:
    """流式回答完成后应立即同步落库，避免前端 hydrate 拉到空消息列表。"""
    service = MentorService(
        agent_factory=AsyncMock(),
        context_service=AsyncMock(),
        rate_limit_service=AsyncMock(),
    )
    fake_session = object()

    from app.services.learning import mentor_service as module

    get_message_mock = AsyncMock(side_effect=[None, None])
    create_message_mock = AsyncMock()
    count_by_session_mock = AsyncMock(return_value=2)
    update_metadata_mock = AsyncMock()

    monkeypatch.setattr(module, "async_session_maker", _FakeSessionMaker(fake_session))
    monkeypatch.setattr(module.chat_message_crud, "get", get_message_mock)
    monkeypatch.setattr(module.chat_message_crud, "create_message", create_message_mock)
    monkeypatch.setattr(module.chat_message_crud, "count_by_session", count_by_session_mock)
    monkeypatch.setattr(module.chat_session_crud, "update_metadata", update_metadata_mock)

    await service._persist_chat_round(
        current_user=SimpleNamespace(id="user-1"),
        request=MentorChatRequest(
            message="请解释一下当前章节",
            session_id="session-1",
            agent_type="company",
            model_id="google/gemini-3.1-pro-preview",
            context=MentorChatContext(
                roadmap_id="roadmap-1",
                concept_id="concept-1",
                concept_title="Hooks",
            ),
        ),
        session_id="session-1",
        trace_id="trace-1",
        user_message_id="user-msg-1",
        assistant_message_id="assistant-msg-1",
        assistant_message="这是导师回复。\n---\n当你进行**切片（Slicing）**操作时：",
    )

    assert create_message_mock.await_count == 2
    create_message_mock.assert_any_await(
        fake_session,
        message_id="user-msg-1",
        session_id="session-1",
        role="user",
        content="请解释一下当前章节",
        agent_type="company",
        model_id="google/gemini-3.1-pro-preview",
        trace_id="trace-1",
        message_metadata={
            "roadmap_id": "roadmap-1",
            "concept_id": "concept-1",
        },
    )
    create_message_mock.assert_any_await(
        fake_session,
        message_id="assistant-msg-1",
        session_id="session-1",
        role="assistant",
        content="这是导师回复。\n\n当你进行 **切片（Slicing）** 操作时：",
        agent_type="company",
        model_id="google/gemini-3.1-pro-preview",
        trace_id="trace-1",
        message_metadata={
            "roadmap_id": "roadmap-1",
            "concept_id": "concept-1",
        },
    )
    count_by_session_mock.assert_awaited_once_with(fake_session, "session-1")
    update_metadata_mock.assert_awaited_once_with(
        fake_session,
        "session-1",
        message_count=2,
        last_message_preview="这是导师回复。\n\n当你进行 **切片（Slicing）** 操作时：",
        title="Hooks",
        model_id="google/gemini-3.1-pro-preview",
        agent_type="company",
    )


def test_sanitize_assistant_message_removes_separator_and_fixes_inline_spacing() -> None:
    """回复清洗应移除水平分隔线，并修正中文与行内 Markdown 之间的空格。"""
    raw_message = "先看结论。\n---\n当你进行**切片（Slicing）**操作时，也可以打印`arr[1:3]`看看。"

    sanitized_message = MentorService._sanitize_assistant_message(raw_message)

    assert "---" not in sanitized_message
    assert "当你进行 **切片（Slicing）** 操作时" in sanitized_message
    assert "打印 `arr[1:3]` 看看" in sanitized_message


def test_build_incremental_sanitized_delta_holds_back_unstable_tail_until_final() -> None:
    """流式清洗应延迟输出尾部，最终再一次性补齐剩余文本。"""
    raw_message = "这是导师回复。\n---\n当你进行**切片（Slicing）**操作时："

    first_delta, emitted_length = MentorService._build_incremental_sanitized_delta(
        raw_text=raw_message,
        emitted_length=0,
    )
    final_delta, final_length = MentorService._build_incremental_sanitized_delta(
        raw_text=raw_message,
        emitted_length=emitted_length,
        is_final=True,
    )

    assert first_delta
    assert "---" not in f"{first_delta}{final_delta}"
    assert f"{first_delta}{final_delta}" == "这是导师回复。\n\n当你进行 **切片（Slicing）** 操作时："
    assert final_length == len("这是导师回复。\n\n当你进行 **切片（Slicing）** 操作时：")


def test_build_stream_error_message_for_authentication_error() -> None:
    """鉴权失败时应返回可直接展示给前端的明确提示。"""
    auth_error = AuthenticationError.__new__(AuthenticationError)

    message = MentorService._build_stream_error_message(auth_error)

    assert "鉴权失败" in message
    assert "API Key" in message


def test_build_stream_error_message_for_bad_request_error() -> None:
    """模型名称错误时应提示用户切换模型名称。"""
    bad_request_error = BadRequestError.__new__(BadRequestError)

    message = MentorService._build_stream_error_message(bad_request_error)

    assert "模型名称" in message
    assert "切换" in message
