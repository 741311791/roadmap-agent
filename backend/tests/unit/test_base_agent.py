"""
BaseAgent 单元测试。
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.agents.base import BaseAgent


class DummyAgent(BaseAgent):
    """用于测试 BaseAgent 通用行为的最小实现。"""

    def __init__(self):
        super().__init__(
            agent_id="dummy_agent",
            model_provider="openai",
            model_name="gpt-4o-mini",
            api_key="test-key",
        )

    async def execute(self, input_data):
        """测试占位方法。"""
        return input_data


def create_response(content, tool_calls=None, finish_reason: str = "stop"):
    """创建模拟的 OpenAI 响应对象。"""
    message = SimpleNamespace(
        content=content,
        tool_calls=tool_calls or [],
    )
    choice = SimpleNamespace(
        message=message,
        finish_reason=finish_reason,
    )
    return SimpleNamespace(
        choices=[choice],
        usage=None,
    )


class TestBaseAgent:
    """测试 BaseAgent 的通用容错逻辑。"""

    def test_extract_message_text_supports_segmented_content(self):
        """分段 content 应被规范化为纯文本。"""
        agent = DummyAgent()
        message = SimpleNamespace(
            content=[
                {"type": "text", "text": "第一段"},
                SimpleNamespace(text="第二段"),
                "第三段",
                {"type": "image_url", "image_url": "https://example.com/image.png"},
            ]
        )

        assert agent._extract_message_text(message) == "第一段\n第二段\n第三段"

    @pytest.mark.asyncio
    async def test_react_forces_completion_when_final_message_is_empty(self):
        """ReAct 最终返回空正文时应追加一次禁止工具的收束调用。"""
        agent = DummyAgent()
        initial_response = create_response(content="", tool_calls=[])
        recovered_response = create_response(content='{"status":"ok"}', tool_calls=[])

        agent._standard_call = AsyncMock(
            side_effect=[initial_response, recovered_response]
        )

        response = await agent._call_llm_with_tools_react(
            messages=[{"role": "user", "content": "请给出最终结果"}],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "web_search",
                        "description": "搜索工具",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                        },
                    },
                }
            ],
            max_iterations=3,
        )

        assert response is recovered_response
        assert agent._standard_call.await_count == 2
        assert agent._standard_call.await_args_list[1].kwargs["tool_choice"] == "none"
