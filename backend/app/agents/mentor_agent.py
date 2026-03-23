"""
AI 伴学助手 Agent
"""
from typing import AsyncGenerator

import structlog
from openai import AuthenticationError
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.config.settings import Settings

logger = structlog.get_logger()


class MentorAgentInput(BaseModel):
    """
    AI 伴学助手输入
    """
    user_message: str = Field(..., description="用户当前输入")
    history_messages: list[dict[str, str]] = Field(default_factory=list, description="短期上下文消息")
    concept_title: str | None = Field(None, description="当前概念标题")
    tutorial_excerpt: str | None = Field(None, description="当前教程摘要")
    roadmap_context: str | None = Field(None, description="路线图上下文摘要")
    ltm_facts: list[str] = Field(default_factory=list, description="长期记忆事实列表")
    ltm_preferences: list[str] = Field(default_factory=list, description="学习偏好记忆")
    ltm_goals: list[str] = Field(default_factory=list, description="学习目标记忆")
    ltm_misconceptions: list[str] = Field(default_factory=list, description="历史误区记忆")
    ltm_progress: list[str] = Field(default_factory=list, description="当前进展记忆")
    ltm_other_facts: list[str] = Field(default_factory=list, description="其他长期记忆")
    learning_profile: str | None = Field(None, description="学习画像摘要")


class MentorAgent(BaseAgent):
    """
    AI 伴学助手 Agent

    功能：
    - 根据不同模式加载不同 Prompt 模板
    - 结合短期记忆与长期记忆进行流式对话
    - 使用 OpenAI 兼容接口输出逐段文本
    """

    agent_id = "mentor_agent"

    @staticmethod
    def _resolve_client_config(
        settings: Settings,
        resolved_model_name: str,
    ) -> tuple[str | None, str | None]:
        """
        根据模型名称解析兼容的网关配置

        说明：
        - 前端允许用户在多个供应商模型之间切换
        - 若后端始终固定使用 MENTOR_AGENT_BASE_URL/API_KEY，模型名与网关不匹配时会直接鉴权失败
        - 这里先按已配置的模型族做最小路由，确保 `google/*` 使用 Gemini 兼容网关
        """
        default_base_url = settings.MENTOR_AGENT_BASE_URL
        default_api_key = settings.get_mentor_agent_api_key

        if resolved_model_name.startswith("google/"):
            return (
                getattr(settings, "get_gemini_openai_base_url", None) or default_base_url,
                getattr(settings, "GEMINI_API_KEY", None) or default_api_key,
            )

        return default_base_url, default_api_key

    def __init__(
        self,
        settings: Settings,
        *,
        agent_type: str = "tutoring",
        model_name: str | None = None,
    ) -> None:
        """
        初始化 AI 伴学助手 Agent
        """
        requested_model_name = (model_name or "").strip()
        resolved_model_name = requested_model_name or settings.MENTOR_AGENT_MODEL
        resolved_base_url, resolved_api_key = self._resolve_client_config(settings, resolved_model_name)
        super().__init__(
            agent_id=self.agent_id,
            model_provider=settings.MENTOR_AGENT_PROVIDER,
            model_name=resolved_model_name,
            base_url=resolved_base_url,
            api_key=resolved_api_key,
            temperature=settings.MENTOR_AGENT_TEMPERATURE,
            max_tokens=settings.MENTOR_AGENT_MAX_TOKENS,
        )
        self._agent_type = agent_type
        self.requested_model_name = resolved_model_name

    def _get_template_name(self) -> str:
        """
        获取 Prompt 模板名称
        """
        if self._agent_type == "company":
            return "company_agent.j2"
        return "tutorin_agent.j2"

    def _render_system_prompt(self, input_data: MentorAgentInput) -> str:
        """
        渲染系统 Prompt
        """
        return self.prompt_loader.render(
            self._get_template_name(),
            concept_title=input_data.concept_title,
            tutorial_excerpt=input_data.tutorial_excerpt,
            roadmap_context=input_data.roadmap_context,
            ltm_facts=input_data.ltm_facts,
            ltm_preferences=input_data.ltm_preferences,
            ltm_goals=input_data.ltm_goals,
            ltm_misconceptions=input_data.ltm_misconceptions,
            ltm_progress=input_data.ltm_progress,
            ltm_other_facts=input_data.ltm_other_facts,
            learning_profile=input_data.learning_profile,
        )

    def _build_messages(self, input_data: MentorAgentInput) -> list[dict[str, str]]:
        """
        组装模型输入消息
        """
        system_prompt = self._render_system_prompt(input_data)
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(input_data.history_messages)
        messages.append({"role": "user", "content": input_data.user_message})
        return messages

    async def stream_chat(self, input_data: MentorAgentInput) -> AsyncGenerator[str, None]:
        """
        执行流式对话
        """
        messages = self._build_messages(input_data)
        try:
            stream = await self._client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                stream=True,
            )
        except AuthenticationError:
            logger.warning(
                "mentor_agent_stream_auth_failed",
                model_name=self.model_name,
            )
            raise

        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def execute(self, input_data: MentorAgentInput) -> str:
        """
        执行非流式对话

        Args:
            input_data: AI 伴学助手输入

        Returns:
            完整回复文本
        """
        chunks: list[str] = []
        async for chunk in self.stream_chat(input_data):
            chunks.append(chunk)
        return "".join(chunks).strip()
