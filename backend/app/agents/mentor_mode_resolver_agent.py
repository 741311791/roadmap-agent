"""
AI 伴学助手回答模式解析 Agent
"""
import json

from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.config.settings import Settings
from app.schemas.mentor import MentorAgentType, MentorAssistMode, MentorResolvedAssistMode
from app.schemas.mentor_model import MentorModelRuntimeConfig


class MentorModeResolverAgentInput(BaseModel):
    """
    回答模式解析输入

    Args:
        user_message: 用户当前输入
        assist_mode: 前端传入的帮助模式
        agent_type: 当前会话的 Agent 类型
        intent_hint: 前端快捷动作提供的软意图提示
        history_message_count: 当前短期上下文消息数
        recent_history_messages: 最近几轮对话摘要

    Returns:
        无

    Raises:
        无
    """

    user_message: str = Field(..., description="用户当前输入")
    assist_mode: MentorAssistMode = Field(default="auto", description="前端当前帮助模式")
    agent_type: MentorAgentType = Field(default="tutoring", description="当前会话 Agent 类型")
    intent_hint: MentorResolvedAssistMode | None = Field(None, description="前端快捷动作提供的软意图提示")
    history_message_count: int = Field(default=0, ge=0, description="当前短期上下文消息数")
    recent_history_messages: list[dict[str, str]] = Field(default_factory=list, description="最近几轮对话")


class MentorModeResolverAgentOutput(BaseModel):
    """
    回答模式解析输出

    Args:
        resolved_assist_mode: 本轮建议回答模式
        confidence: 解析置信度，范围为 0 到 1
        reason: 简短判断依据，便于日志排查

    Returns:
        无

    Raises:
        无
    """

    resolved_assist_mode: MentorResolvedAssistMode = Field(..., description="本轮建议回答模式")
    confidence: float = Field(..., ge=0.0, le=1.0, description="解析置信度")
    reason: str = Field(..., min_length=1, max_length=200, description="简短判断依据")


class MentorModeResolverAgent(BaseAgent):
    """
    使用轻量模型解析 AI 伴学助手的回答模式

    功能：
    - 基于用户输入和最近对话判断更适合的回答模式
    - 输出结构化的模式与置信度
    - 供 MentorService 在低置信度时回退到规则匹配
    """

    agent_id = "mentor_mode_resolver_agent"

    def __init__(
        self,
        settings: Settings,
        runtime_config: MentorModelRuntimeConfig | None = None,
    ) -> None:
        """
        初始化回答模式解析 Agent

        Args:
            settings: 应用配置

        Returns:
            无

        Raises:
            无
        """
        resolved_runtime_config = runtime_config or MentorModelRuntimeConfig(
            model_id=settings.get_mentor_mode_resolver_model,
            display_name=settings.get_mentor_mode_resolver_model,
            provider=settings.MENTOR_MODE_RESOLVER_PROVIDER,
            model_name=settings.get_mentor_mode_resolver_model,
            base_url=settings.get_mentor_mode_resolver_base_url,
            api_key=settings.get_mentor_mode_resolver_api_key,
            supports_streaming=False,
            supports_structured_output=True,
            supports_tools=False,
            source="fallback",
        )
        super().__init__(
            agent_id=self.agent_id,
            model_provider=resolved_runtime_config.provider,
            model_name=resolved_runtime_config.model_name,
            base_url=resolved_runtime_config.base_url,
            api_key=resolved_runtime_config.api_key,
            temperature=settings.MENTOR_MODE_RESOLVER_TEMPERATURE,
            max_tokens=settings.MENTOR_MODE_RESOLVER_MAX_TOKENS,
        )

    async def execute(self, input_data: MentorModeResolverAgentInput | dict) -> MentorModeResolverAgentOutput:
        """
        解析本轮回答模式

        Args:
            input_data: 回答模式解析输入

        Returns:
            结构化的回答模式解析结果

        Raises:
            Exception: 当底层模型调用失败时向上抛出
        """
        if not isinstance(input_data, MentorModeResolverAgentInput):
            input_data = MentorModeResolverAgentInput.model_validate(input_data)

        system_prompt = self.prompt_loader.render(
            "mentor_mode_resolver.j2",
            output_schema=MentorModeResolverAgentOutput.model_json_schema(),
        )
        recent_history_lines = [
            f"{message.get('role', 'unknown')}: {message.get('content', '')}"
            for message in input_data.recent_history_messages[-6:]
            if message.get("content")
        ]
        user_payload = {
            "user_message": input_data.user_message,
            "assist_mode": input_data.assist_mode,
            "agent_type": input_data.agent_type,
            "intent_hint": input_data.intent_hint,
            "history_message_count": input_data.history_message_count,
            "recent_history_messages": recent_history_lines,
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, indent=2)},
        ]
        return await self.call_llm(messages, response_model=MentorModeResolverAgentOutput)
