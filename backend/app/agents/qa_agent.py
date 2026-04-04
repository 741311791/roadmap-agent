"""
答疑 Agent
"""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from app.agents.base import BaseAgent
from app.config.settings import Settings
from app.schemas.mentor_model import MentorModelRuntimeConfig
from app.services.learning.mentor.event_types import (
    MentorQaAgentInput,
    MentorStreamEvent,
)
from app.services.learning.mentor.runtime_factory import MentorRuntimeFactory
from app.tools.registry import ToolRegistry


class QaAgent(BaseAgent):
    """
    基于 LangChain / LangGraph 的答疑 Agent façade
    """

    agent_id = "qa_agent"

    def __init__(
        self,
        settings: Settings,
        *,
        runtime_config: MentorModelRuntimeConfig,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        super().__init__(
            agent_id=self.agent_id,
            model_provider=runtime_config.provider,
            model_name=runtime_config.model_name,
            base_url=runtime_config.base_url,
            api_key=runtime_config.api_key,
            temperature=settings.MENTOR_AGENT_TEMPERATURE,
            max_tokens=settings.MENTOR_AGENT_MAX_TOKENS,
        )
        self.settings = settings
        self.runtime_config = runtime_config
        self.runtime_factory = MentorRuntimeFactory(
            settings=settings,
            tool_registry=tool_registry,
        )

    @staticmethod
    def get_template_name() -> str:
        """
        获取 Prompt 模板名称
        """

        return "qa_agent.j2"

    @staticmethod
    def get_current_date_string() -> str:
        """
        获取当前日期字符串
        """

        return datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d")

    async def stream_chat(
        self,
        input_data: MentorQaAgentInput,
    ) -> AsyncGenerator[MentorStreamEvent, None]:
        """
        执行流式对话
        """

        runner = self.runtime_factory.create_qa_runner(
            runtime_config=self.runtime_config,
        )
        async for event in runner.stream_chat(input_data):
            yield event

    async def execute(self, input_data: MentorQaAgentInput) -> str:
        """
        执行非流式对话
        """

        chunks: list[str] = []
        async for event in self.stream_chat(input_data):
            if event.type == "text_delta":
                chunks.append(event.delta)
        return "".join(chunks).strip()
