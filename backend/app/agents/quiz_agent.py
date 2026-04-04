"""
测验 Agent 占位实现
"""

from collections.abc import AsyncGenerator

from app.agents.base import BaseAgent
from app.config.settings import Settings
from app.schemas.mentor_model import MentorModelRuntimeConfig
from app.services.learning.mentor.event_types import (
    MentorPlaceholderAgentInput,
    MentorTextDeltaEvent,
)


class QuizAgent(BaseAgent):
    """
    测验 Agent 占位实现
    """

    agent_id = "quiz_agent"

    def __init__(
        self,
        settings: Settings,
        *,
        runtime_config: MentorModelRuntimeConfig,
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

    async def stream_chat(
        self,
        input_data: MentorPlaceholderAgentInput,
    ) -> AsyncGenerator[MentorTextDeltaEvent, None]:
        """
        返回测验模式占位提示
        """

        chapter_suffix = f"「{input_data.concept_title}」" if input_data.concept_title else "当前章节"
        yield MentorTextDeltaEvent(
            delta=(
                f"测验 Agent 正在建设中。后续这里会支持围绕 {chapter_suffix} 自动出题、"
                "即时判分和针对性讲解。当前建议先切到答疑模式，把卡点讲明白。"
            )
        )

    async def execute(self, input_data: MentorPlaceholderAgentInput) -> str:
        """
        执行非流式对话
        """

        chunks: list[str] = []
        async for event in self.stream_chat(input_data):
            chunks.append(event.delta)
        return "".join(chunks).strip()
