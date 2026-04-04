"""
答疑 Agent 的 LangChain / LangGraph 运行器
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

from langchain.agents import create_agent
from langchain_litellm import ChatLiteLLM

from app.config.settings import Settings
from app.schemas.mentor_model import MentorModelRuntimeConfig
from app.services.learning.mentor.event_types import (
    MentorThinkingDeltaEvent,
    MentorQaAgentInput,
    MentorStreamEvent,
    MentorTextDeltaEvent,
    MentorToolResultEvent,
    MentorToolStartEvent,
)
from app.services.learning.mentor.prompt_builder import QaPromptBuilder
from app.services.learning.mentor.tool_executor import MentorToolExecutor
from app.services.learning.mentor.tool_policy import MentorToolPolicy


class QaAgentGraphRunner:
    """
    使用 LangChain create_agent 驱动的答疑 Agent 运行器

    说明：
    - `create_agent` 底层由 LangGraph 编排 tool loop。
    - 当前运行器主要负责把 LangChain 事件流转换为现有前端可消费的中性事件。
    """

    def __init__(
        self,
        *,
        settings: Settings,
        runtime_config: MentorModelRuntimeConfig,
        prompt_builder: QaPromptBuilder,
        tool_policy: MentorToolPolicy,
        tool_executor: MentorToolExecutor,
    ) -> None:
        self.settings = settings
        self.runtime_config = runtime_config
        self.prompt_builder = prompt_builder
        self.tool_policy = tool_policy
        self.tool_executor = tool_executor

    @staticmethod
    def _get_current_date_string() -> str:
        """
        获取当前日期字符串
        """

        return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")

    def _build_langchain_model_identifier(self) -> str:
        """
        构建 ChatLiteLLM 所需的模型标识
        """

        base_url = self.runtime_config.base_url or ""
        model_name = self.runtime_config.model_name
        if "dashscope" in base_url and not model_name.startswith("dashscope/"):
            return f"dashscope/{model_name}"
        return model_name

    @staticmethod
    def _extract_text_from_chunk(chunk: Any) -> str:
        """
        从 LangChain chunk / message 中提取文本内容
        """

        if chunk is None:
            return ""

        if isinstance(chunk, str):
            return chunk

        if isinstance(chunk, dict):
            text_value = chunk.get("text")
            if isinstance(text_value, str):
                return text_value

            content_value = chunk.get("content")
            if content_value is not None:
                return QaAgentGraphRunner._extract_text_from_chunk(content_value)

            messages_value = chunk.get("messages")
            if isinstance(messages_value, list) and messages_value:
                return QaAgentGraphRunner._extract_text_from_chunk(messages_value[-1])

        if isinstance(chunk, list):
            text_parts: list[str] = []
            for part in chunk:
                if isinstance(part, dict) and part.get("type") in {"reasoning", "thinking"}:
                    continue

                text_part = QaAgentGraphRunner._extract_text_from_chunk(part)
                if text_part:
                    text_parts.append(text_part)

            return "".join(text_parts)

        content = getattr(chunk, "content", None)

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            text_parts: list[str] = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                    continue
                if isinstance(part, dict):
                    if part.get("type") in {"reasoning", "thinking"}:
                        continue
                    if part.get("type") == "text" and isinstance(part.get("text"), str):
                        text_parts.append(part["text"])
                        continue
                    if isinstance(part.get("text"), str):
                        text_parts.append(part["text"])
                        continue
                text = getattr(part, "text", None)
                if isinstance(text, str):
                    text_parts.append(text)
            return "".join(text_parts)

        text = getattr(chunk, "text", None)
        if isinstance(text, str):
            return text

        return ""

    @staticmethod
    def _extract_reasoning_from_chunk(chunk: Any) -> str:
        """
        从 LangChain chunk / message 中提取思考增量
        """

        if chunk is None:
            return ""

        if isinstance(chunk, dict):
            reasoning_value = chunk.get("reasoning") or chunk.get("reasoning_content")
            if isinstance(reasoning_value, str):
                return reasoning_value

            content_value = chunk.get("content") or chunk.get("content_blocks")
            if isinstance(content_value, list):
                reasoning_parts: list[str] = []
                for part in content_value:
                    if not isinstance(part, dict):
                        continue

                    if part.get("type") in {"reasoning", "thinking"}:
                        candidate = part.get("reasoning") or part.get("thinking") or part.get("text")
                        if isinstance(candidate, str):
                            reasoning_parts.append(candidate)
                            continue

                    candidate = part.get("reasoning_content")
                    if isinstance(candidate, str):
                        reasoning_parts.append(candidate)

                return "".join(reasoning_parts)

        additional_kwargs = getattr(chunk, "additional_kwargs", None)
        if isinstance(additional_kwargs, dict):
            reasoning_value = additional_kwargs.get("reasoning_content")
            if isinstance(reasoning_value, str):
                return reasoning_value

        content_blocks = getattr(chunk, "content_blocks", None)
        if isinstance(content_blocks, list):
            reasoning_parts: list[str] = []
            for block in content_blocks:
                if not isinstance(block, dict):
                    continue

                if block.get("type") in {"reasoning", "thinking"}:
                    candidate = block.get("reasoning") or block.get("thinking") or block.get("text")
                    if isinstance(candidate, str):
                        reasoning_parts.append(candidate)
                        continue

                candidate = block.get("reasoning_content")
                if isinstance(candidate, str):
                    reasoning_parts.append(candidate)

            return "".join(reasoning_parts)

        reasoning_value = getattr(chunk, "reasoning", None)
        if isinstance(reasoning_value, str):
            return reasoning_value

        return ""

    @staticmethod
    def _build_missing_text_delta(*, full_text: str, streamed_text: str) -> str:
        """
        基于最终完整文本，计算尚未向上游发送的剩余文本
        """

        if not full_text:
            return ""

        if not streamed_text:
            return full_text

        shared_prefix_length = 0
        max_prefix_length = min(len(full_text), len(streamed_text))
        while (
            shared_prefix_length < max_prefix_length
            and full_text[shared_prefix_length] == streamed_text[shared_prefix_length]
        ):
            shared_prefix_length += 1

        return full_text[shared_prefix_length:]

    def _create_runtime_agent(self, input_data: MentorQaAgentInput):
        """
        创建 LangChain Agent 运行实例
        """

        model = ChatLiteLLM(
            model=self._build_langchain_model_identifier(),
            api_key=self.runtime_config.api_key,
            api_base=self.runtime_config.base_url or None,
            temperature=self.settings.MENTOR_AGENT_TEMPERATURE,
            max_tokens=self.settings.MENTOR_AGENT_MAX_TOKENS,
        )
        current_date = self._get_current_date_string()
        system_prompt = self.prompt_builder.build_system_prompt(
            input_data,
            current_date=current_date,
        )
        tools = self.tool_executor.build_langchain_tools(
            allowed_tool_names=self.tool_policy.get_allowed_tool_names(),
            argument_enricher=lambda tool_name, arguments: self.tool_policy.enrich_tool_arguments(
                tool_name=tool_name,
                arguments=arguments,
                input_data=input_data,
            ),
        )

        return create_agent(
            model=model,
            tools=tools,
            system_prompt=system_prompt,
        )

    async def stream_chat(
        self,
        input_data: MentorQaAgentInput,
    ) -> AsyncGenerator[MentorStreamEvent, None]:
        """
        执行答疑 Agent 流式对话
        """

        agent = self._create_runtime_agent(input_data)
        messages = self.prompt_builder.build_messages(
            input_data,
            current_date=self._get_current_date_string(),
        )
        streamed_text = ""
        streamed_reasoning = ""
        tool_arguments_by_call_id: dict[str, dict[str, Any]] = {}
        async for event in agent.astream_events(
            {"messages": messages},
            version="v2",
            config={"recursion_limit": 20},
        ):
            event_name = event.get("event")

            if event_name == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                reasoning_delta = self._extract_reasoning_from_chunk(chunk)
                if reasoning_delta:
                    streamed_reasoning += reasoning_delta
                    yield MentorThinkingDeltaEvent(delta=reasoning_delta)

                text_delta = self._extract_text_from_chunk(chunk)
                if text_delta:
                    streamed_text += text_delta
                    yield MentorTextDeltaEvent(delta=text_delta)
                continue

            if event_name == "on_chat_model_end":
                output = event.get("data", {}).get("output")
                full_reasoning = self._extract_reasoning_from_chunk(output)
                missing_reasoning = self._build_missing_text_delta(
                    full_text=full_reasoning,
                    streamed_text=streamed_reasoning,
                )
                if missing_reasoning:
                    streamed_reasoning += missing_reasoning
                    yield MentorThinkingDeltaEvent(delta=missing_reasoning)

                full_text = self._extract_text_from_chunk(output)
                missing_text = self._build_missing_text_delta(
                    full_text=full_text,
                    streamed_text=streamed_text,
                )
                if missing_text:
                    streamed_text += missing_text
                    yield MentorTextDeltaEvent(delta=missing_text)
                continue

            if event_name == "on_tool_start":
                raw_arguments = event.get("data", {}).get("input") or {}
                if not isinstance(raw_arguments, dict):
                    raw_arguments = {"value": raw_arguments}
                tool_call_id = str(event.get("run_id") or event.get("name") or "tool-call")
                tool_arguments_by_call_id[tool_call_id] = raw_arguments
                yield MentorToolStartEvent(
                    tool_call_id=tool_call_id,
                    tool_name=str(event.get("name") or "tool"),
                    arguments=raw_arguments,
                )
                continue

            if event_name == "on_tool_end":
                raw_output = event.get("data", {}).get("output")
                serialized_result = self.tool_executor.serialize_tool_result(raw_output)
                tool_call_id = str(event.get("run_id") or event.get("name") or "tool-call")
                yield MentorToolResultEvent(
                    tool_call_id=tool_call_id,
                    tool_name=str(event.get("name") or "tool"),
                    arguments=tool_arguments_by_call_id.get(tool_call_id, {}),
                    result=serialized_result,
                    is_error=self.tool_executor.is_error_result(serialized_result),
                )
