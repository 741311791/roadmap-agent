from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from openai import AuthenticationError, BadRequestError

from app.api.v1.endpoints.learning.mentor import _normalize_agent_kind
from app.schemas.mentor import MentorChatContext, MentorChatRequest
from app.services.learning.mentor import MentorEmotionAnalysis
from app.services.learning.mentor_service import MentorChatAgentContext, MentorService


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


def build_agent_context(
    *,
    agent_kind: str = "qa",
    qa_style: str | None = "serious",
    emotion_label: str = "anxious",
    emotion_summary: str = "用户明显卡住，需要先安抚再解释。",
) -> MentorChatAgentContext:
    """构造测试用 Agent 上下文。"""

    return MentorChatAgentContext(
        agent_kind=agent_kind,
        qa_style=qa_style,
        emotion=MentorEmotionAnalysis(
            label=emotion_label,
            summary=emotion_summary,
        ),
    )


@pytest.mark.asyncio
async def test_persist_chat_round_writes_messages_and_updates_session(monkeypatch) -> None:
    """流式回答完成后应立即同步落库，并写入新的 agentKind / qaStyle 元数据。"""

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
            agent_kind="qa",
            qa_style="serious",
            model_id="google/gemini-3.1-pro-preview",
            context=MentorChatContext(
                roadmap_id="roadmap-1",
                concept_id="concept-1",
                concept_title="Hooks",
            ),
        ),
        model_id="google/gemini-3.1-pro-preview",
        session_id="session-1",
        trace_id="trace-1",
        user_message_id="user-msg-1",
        assistant_message_id="assistant-msg-1",
        assistant_message="这是导师回复。\n---\n当你进行**切片（Slicing）**操作时：",
        assistant_content_parts=[
            {
                "type": "tool-call",
                "toolCallId": "tool-1",
                "toolName": "web_search",
                "arguments": {"query": "python slicing"},
                "state": "completed",
                "result": "Found latest docs",
                "isError": False,
            },
            {
                "type": "text",
                "text": "这是导师回复。\n\n当你进行 **切片（Slicing）** 操作时：",
            },
        ],
        agent_context=build_agent_context(),
    )

    assert create_message_mock.await_count == 2
    user_call = create_message_mock.await_args_list[0]
    assistant_call = create_message_mock.await_args_list[1]

    assert user_call.kwargs["agent_type"] == "qa"
    assert user_call.kwargs["intent_type"] == "qa"
    assert user_call.kwargs["message_metadata"]["agentKind"] == "qa"
    assert user_call.kwargs["message_metadata"]["qaStyle"] == "serious"
    assert user_call.kwargs["message_metadata"]["emotionLabel"] == "anxious"

    assert assistant_call.kwargs["content"] == "这是导师回复。\n\n当你进行 **切片（Slicing）** 操作时："
    assert assistant_call.kwargs["agent_type"] == "qa"
    assert assistant_call.kwargs["message_metadata"]["contentParts"][0]["toolName"] == "web_search"
    assert assistant_call.kwargs["message_metadata"]["qaStyle"] == "serious"

    count_by_session_mock.assert_awaited_once_with(fake_session, "session-1")
    update_metadata_mock.assert_awaited_once_with(
        fake_session,
        "session-1",
        message_count=2,
        last_message_preview="这是导师回复。\n\n当你进行 **切片（Slicing）** 操作时：",
        title="Hooks",
        model_id="google/gemini-3.1-pro-preview",
        agent_type="qa",
    )


def test_build_message_metadata_contains_new_agent_fields() -> None:
    """消息元数据应包含 agentKind、qaStyle 和情绪字段。"""

    request = MentorChatRequest(
        message="我有点卡住了",
        session_id="session-1",
        agent_kind="qa",
        qa_style="casual",
        context=MentorChatContext(
            roadmap_id="roadmap-1",
            concept_id="concept-1",
            concept_title="Hooks",
        ),
    )

    metadata = MentorService._build_message_metadata(
        request=request,
        agent_context=build_agent_context(
            qa_style="casual",
            emotion_label="anxious",
            emotion_summary="用户语气焦虑，需要先降低心理负担。",
        ),
        content_parts=[{"type": "text", "text": "你好"}],
    )

    assert metadata["agentKind"] == "qa"
    assert metadata["qaStyle"] == "casual"
    assert metadata["emotionLabel"] == "anxious"
    assert metadata["emotionSummary"] == "用户语气焦虑，需要先降低心理负担。"
    assert metadata["contentParts"][0]["text"] == "你好"


def test_analyze_user_emotion_identifies_anxious_users() -> None:
    """带有卡住和不会等表达时，应识别为 anxious。"""

    emotion = MentorService._analyze_user_emotion("我还是不会，真的有点卡住了")

    assert emotion.label == "anxious"
    assert "卡住" in emotion.summary


def test_analyze_user_emotion_identifies_frustrated_users() -> None:
    """排错语气应识别为 frustrated。"""

    emotion = MentorService._analyze_user_emotion("为什么还是报错，怎么不行")

    assert emotion.label == "frustrated"


def test_sanitize_assistant_message_removes_separator_and_fixes_inline_spacing() -> None:
    """回复清洗应移除水平分隔线，并修正中文与行内 Markdown 之间的空格。"""

    raw_message = "先看结论。\n---\n当你进行**切片（Slicing）**操作时，也可以打印`arr[1:3]`看看。"

    sanitized_message = MentorService._sanitize_assistant_message(raw_message)

    assert "---" not in sanitized_message
    assert "当你进行 **切片（Slicing）** 操作时" in sanitized_message
    assert "打印 `arr[1:3]` 看看" in sanitized_message


def test_sanitize_assistant_message_removes_emoji_and_normalizes_double_backticks() -> None:
    """回复清洗应去掉 emoji，并把双反引号改成标准行内代码。"""

    raw_message = "✅ 一句话定义：\n👉 ``ndarray`` 是 NumPy 的核心对象。🧩"

    sanitized_message = MentorService._sanitize_assistant_message(raw_message)

    assert "✅" not in sanitized_message
    assert "👉" not in sanitized_message
    assert "🧩" not in sanitized_message
    assert "``ndarray``" not in sanitized_message
    assert "`ndarray`" in sanitized_message


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


def test_append_thinking_content_part_merges_adjacent_blocks() -> None:
    """相邻思考片段应合并为单个 thinking block，便于前端折叠展示。"""

    content_parts: list[dict] = []

    MentorService._append_thinking_content_part(content_parts, "先分析问题。")
    MentorService._append_thinking_content_part(content_parts, "再检查上下文。")

    assert content_parts == [
        {
            "type": "thinking",
            "text": "先分析问题。再检查上下文。",
        }
    ]


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


def test_normalize_agent_kind_maps_legacy_company_and_tutoring_to_qa() -> None:
    """历史会话里的 company / tutoring 应兼容映射到 qa。"""

    assert _normalize_agent_kind("company") == "qa"
    assert _normalize_agent_kind("tutoring") == "qa"
    assert _normalize_agent_kind("qa") == "qa"


def test_normalize_agent_kind_falls_back_to_qa_for_unknown_session_values() -> None:
    """未知旧值不应让会话列表 500，而应回退到 qa。"""

    assert _normalize_agent_kind("legacy_mode") == "qa"
    assert _normalize_agent_kind(None) == "qa"
    assert _normalize_agent_kind("legacy_mode", allow_none=True) is None


@pytest.mark.asyncio
async def test_dispatch_memory_job_includes_langfuse_trace_id_and_new_agent_fields(monkeypatch) -> None:
    """投递记忆任务时应带上 Langfuse Trace、agent_kind、qa_style 与情绪字段。"""

    service = MentorService(
        agent_factory=AsyncMock(),
        context_service=AsyncMock(),
        rate_limit_service=AsyncMock(),
    )
    fake_session = object()

    from app.services.learning import mentor_service as module

    send_task_mock = Mock(return_value=SimpleNamespace(id="celery-task-1"))
    create_job_mock = AsyncMock()

    monkeypatch.setattr(module, "async_session_maker", _FakeSessionMaker(fake_session))
    monkeypatch.setattr(module.celery_app, "send_task", send_task_mock)
    monkeypatch.setattr(module.mentor_memory_job_crud, "create_job", create_job_mock)

    await service._dispatch_memory_job(
        current_user=SimpleNamespace(id="user-1"),
        request=MentorChatRequest(
            message="继续解释闭包",
            session_id="session-1",
            agent_kind="qa",
            qa_style="serious",
            context=MentorChatContext(
                roadmap_id="roadmap-1",
                concept_id="concept-1",
                concept_title="闭包",
            ),
        ),
        model_id="google/gemini-3.1-pro-preview",
        resolved_model_name="google/gemini-3.1-pro-preview",
        provider="openai",
        session_id="session-1",
        trace_id="trace-1",
        langfuse_trace_id="1234567890abcdef1234567890abcdef",
        user_message_id="user-msg-1",
        assistant_message_id="assistant-msg-1",
        assistant_message="这是导师回复。",
        agent_context=build_agent_context(
            qa_style="serious",
            emotion_label="curious",
            emotion_summary="用户在追问原理，偏探索型求知。",
        ),
    )

    send_task_mock.assert_called_once()
    _, send_task_kwargs = send_task_mock.call_args
    assert send_task_kwargs["kwargs"]["trace_id"] == "trace-1"
    assert send_task_kwargs["kwargs"]["langfuse_trace_id"] == "1234567890abcdef1234567890abcdef"
    assert send_task_kwargs["kwargs"]["agent_kind"] == "qa"
    assert send_task_kwargs["kwargs"]["qa_style"] == "serious"
    assert send_task_kwargs["kwargs"]["emotion_label"] == "curious"
    create_job_mock.assert_awaited_once()
