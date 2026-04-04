from collections.abc import AsyncGenerator
from unittest.mock import Mock

import pytest

from app.agents.qa_agent import QaAgent
from app.services.learning.mentor.graph_runner import QaAgentGraphRunner
from app.services.learning.mentor import (
    MentorEmotionAnalysis,
    MentorThinkingDeltaEvent,
    MentorQaAgentInput,
    MentorTextDeltaEvent,
    MentorToolResultEvent,
    MentorToolStartEvent,
)


class _DummySettings:
    MENTOR_AGENT_MODEL = "openai/gpt-4.1-mini"
    MENTOR_AGENT_PROVIDER = "openai"
    MENTOR_AGENT_BASE_URL = "https://example.com/v1"
    MENTOR_AGENT_TEMPERATURE = 0.2
    MENTOR_AGENT_MAX_TOKENS = 2048

    @property
    def get_mentor_agent_api_key(self) -> str:
        return "test-key"


class _DummyRuntimeConfig:
    model_id = "openai/gpt-4.1-mini"
    display_name = "GPT-4.1 Mini"
    provider = "openai"
    model_name = "openai/gpt-4.1-mini"
    base_url = "https://example.com/v1"
    api_key = "test-key"
    supports_streaming = True
    supports_structured_output = True
    supports_tools = True
    supports_thinking = False
    source = "test"


def build_input() -> MentorQaAgentInput:
    """构造测试输入。"""

    return MentorQaAgentInput(
        user_message="解释一下 useMemo",
        history_messages=[],
        concept_title="React Hooks",
        qa_style="casual",
        emotion=MentorEmotionAnalysis(
            label="curious",
            summary="用户偏探索式提问。",
        ),
    )


@pytest.mark.asyncio
async def test_qa_agent_execute_joins_text_deltas(monkeypatch) -> None:
    """非流式执行应拼接所有文本增量。"""

    async def fake_stream_chat(self, input_data) -> AsyncGenerator[MentorTextDeltaEvent, None]:
        yield MentorTextDeltaEvent(delta="第一段")
        yield MentorTextDeltaEvent(delta="第二段")

    monkeypatch.setattr("app.services.learning.mentor.graph_runner.QaAgentGraphRunner.stream_chat", fake_stream_chat)

    agent = QaAgent(
        _DummySettings(),
        runtime_config=_DummyRuntimeConfig(),
        tool_registry=None,
    )
    result = await agent.execute(build_input())

    assert result == "第一段第二段"


def test_qa_agent_uses_qa_prompt_template() -> None:
    """答疑 Agent 应始终使用新的 QA Prompt 模板。"""

    assert QaAgent.get_template_name() == "qa_agent.j2"


@pytest.mark.asyncio
async def test_graph_runner_uses_chat_model_end_output_when_stream_chunk_is_empty(monkeypatch) -> None:
    """当网关只在 on_chat_model_end 返回完整文本时，运行器仍应产出文本增量。"""

    class _DummyRuntimeAgent:
        async def astream_events(self, *_args, **_kwargs):
            yield {
                "event": "on_chat_model_start",
                "data": {},
            }
            yield {
                "event": "on_chat_model_end",
                "data": {
                    "output": {
                        "content": "这是最终回答",
                    }
                },
            }

    runner = QaAgentGraphRunner(
        settings=_DummySettings(),
        runtime_config=_DummyRuntimeConfig(),
        prompt_builder=Mock(),
        tool_policy=Mock(),
        tool_executor=Mock(),
    )
    runner.prompt_builder.build_messages.return_value = []
    monkeypatch.setattr(runner, "_create_runtime_agent", lambda _input_data: _DummyRuntimeAgent())

    events = [event async for event in runner.stream_chat(build_input())]

    assert events == [MentorTextDeltaEvent(delta="这是最终回答")]


def test_graph_runner_build_missing_text_delta_only_returns_unstreamed_suffix() -> None:
    """最终消息补发时，只应输出尚未流出的后缀。"""

    missing_text = QaAgentGraphRunner._build_missing_text_delta(
        full_text="这是最终回答",
        streamed_text="这是最",
    )

    assert missing_text == "终回答"


@pytest.mark.asyncio
async def test_graph_runner_preserves_tool_arguments_and_extracts_reasoning(monkeypatch) -> None:
    """运行器应保留工具参数，并把 reasoning block 转为 thinking 事件。"""

    class _DummyRuntimeAgent:
        async def astream_events(self, *_args, **_kwargs):
            yield {
                "event": "on_chat_model_stream",
                "data": {
                    "chunk": {
                        "content": [
                            {
                                "type": "reasoning",
                                "text": "先检索资料。",
                            },
                            {
                                "type": "text",
                                "text": "先给你一个直观理解。",
                            },
                        ]
                    }
                },
            }
            yield {
                "event": "on_tool_start",
                "name": "web_search",
                "run_id": "tool-call-1",
                "data": {
                    "input": {
                        "query": "NumPy broadcasting",
                    }
                },
            }
            yield {
                "event": "on_tool_end",
                "name": "web_search",
                "run_id": "tool-call-1",
                "data": {
                    "output": {
                        "results": [
                            {
                                "title": "Broadcasting - NumPy",
                                "url": "https://numpy.org/doc/stable/user/basics.broadcasting.html",
                            }
                        ]
                    }
                },
            }

    runner = QaAgentGraphRunner(
        settings=_DummySettings(),
        runtime_config=_DummyRuntimeConfig(),
        prompt_builder=Mock(),
        tool_policy=Mock(),
        tool_executor=Mock(),
    )
    runner.prompt_builder.build_messages.return_value = []
    runner.tool_executor.serialize_tool_result.side_effect = lambda value: str(value)
    runner.tool_executor.is_error_result.return_value = False
    monkeypatch.setattr(runner, "_create_runtime_agent", lambda _input_data: _DummyRuntimeAgent())

    events = [event async for event in runner.stream_chat(build_input())]

    assert events == [
      MentorThinkingDeltaEvent(delta="先检索资料。"),
      MentorTextDeltaEvent(delta="先给你一个直观理解。"),
      MentorToolStartEvent(
          tool_call_id="tool-call-1",
          tool_name="web_search",
          arguments={"query": "NumPy broadcasting"},
      ),
      MentorToolResultEvent(
          tool_call_id="tool-call-1",
          tool_name="web_search",
          arguments={"query": "NumPy broadcasting"},
          result=(
              "{'results': [{'title': 'Broadcasting - NumPy', 'url': "
              "'https://numpy.org/doc/stable/user/basics.broadcasting.html'}]}"
          ),
          is_error=False,
      ),
    ]
