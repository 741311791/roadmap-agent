"""
Mentor Agent（伴学/导学双模式，流式输出）。
"""
from __future__ import annotations

from typing import Any, AsyncGenerator

import structlog
from fastapi.encoders import jsonable_encoder
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
from langchain_litellm import ChatLiteLLM
from langgraph.prebuilt import create_react_agent

from app.config.settings import Settings
from app.schemas.mentor import MentorModelName
from app.tools.mcp_loader import load_context7_tools
from app.utils.prompt_loader import PromptLoader

logger = structlog.get_logger(__name__)


class MentorAgent:
    """
    基于 LangGraph ReAct 的 Mentor Agent。

    Args:
        settings: 全局配置对象。

    Returns:
        无。

    Raises:
        ValueError: 当 agent_mode 不合法时抛出。
    """

    AGENT_PROMPT_MAP = {
        "companion": "companion_agent.j2",
        "tutoring": "tutoring_agent.j2",
    }

    def __init__(self, settings: Settings):
        """
        初始化 MentorAgent。

        Args:
            settings: 应用配置对象。

        Returns:
            无。

        Raises:
            RuntimeError: 当模型初始化失败时抛出。
        """

        self.settings = settings
        self.prompt_loader = PromptLoader()

    def _create_llm(self, model_name_override: MentorModelName | None = None) -> ChatLiteLLM:
        """
        创建流式 Chat 模型实例。

        Args:
            model_name_override: 请求级别模型名称覆盖（可选）。

        Returns:
            ChatLiteLLM: 可流式输出的模型实例。

        Raises:
            RuntimeError: 当模型配置不可用时抛出。
        """

        # 为什么这样做：仅在未显式选择模型时回退到 ANALYZER，避免覆盖前端传入的模型选择。
        mentor_api_key = (self.settings.MENTOR_API_KEY or "").strip()
        use_fallback_config = mentor_api_key in {"", "your_openai_api_key_here"}
        should_use_fallback = use_fallback_config and model_name_override is None

        if should_use_fallback:
            model_provider = self.settings.ANALYZER_PROVIDER
            model_name = self.settings.ANALYZER_MODEL
            api_key = self.settings.ANALYZER_API_KEY
            api_base = self.settings.ANALYZER_BASE_URL
            logger.warning(
                "mentor_config_fallback_to_analyzer",
                reason="mentor_api_key_not_configured",
            )
        else:
            model_provider = self.settings.MENTOR_PROVIDER
            model_name = model_name_override or self.settings.MENTOR_MODEL
            api_key = mentor_api_key
            api_base = self.settings.MENTOR_BASE_URL

        if "/" not in model_name and model_provider:
            model_name = f"{model_provider}/{model_name}"

        return ChatLiteLLM(
            model=model_name,
            api_key=api_key,
            api_base=api_base,
            temperature=self.settings.MENTOR_TEMPERATURE,
            streaming=True,
        )

    def _build_system_prompt(
        self,
        agent_mode: str,
        roadmap_title: str,
        current_concept: str | None,
        user_background: str | None,
    ) -> str:
        """
        渲染系统提示词。

        Args:
            agent_mode: Agent 模式。
            roadmap_title: 路线图标题。
            current_concept: 当前概念名称。
            user_background: 用户背景信息。

        Returns:
            str: 渲染后的系统提示词。

        Raises:
            ValueError: 当 agent_mode 不合法时抛出。
        """

        template_name = self.AGENT_PROMPT_MAP.get(agent_mode)
        if not template_name:
            raise ValueError(f"不支持的 agent_mode: {agent_mode}")

        return self.prompt_loader.render(
            template_name,
            roadmap_title=roadmap_title,
            current_concept=current_concept,
            user_background=user_background,
        )

    def _inject_tool_context(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        user_id: str,
        roadmap_id: str,
        concept_id: str | None,
    ) -> dict[str, Any]:
        """
        为工具参数注入上下文默认值。

        Args:
            tool_name: 工具名称。
            tool_args: 模型提供的原始工具参数。
            user_id: 当前用户 ID。
            roadmap_id: 当前路线图 ID。
            concept_id: 当前概念 ID。

        Returns:
            dict[str, Any]: 注入上下文后的参数字典。

        Raises:
            无。
        """

        merged_args = dict(tool_args)

        if tool_name in {"get_roadmap_metadata", "get_concept_tutorial", "mark_content_complete"}:
            merged_args["roadmap_id"] = roadmap_id

        if tool_name in {"get_user_profile", "mark_content_complete"}:
            merged_args["user_id"] = user_id

        if tool_name in {"get_concept_tutorial", "mark_content_complete"} and concept_id:
            merged_args.setdefault("concept_id", concept_id)

        return merged_args

    async def _build_langchain_tools(
        self,
        user_id: str,
        roadmap_id: str,
        concept_id: str | None,
    ) -> list[Any]:
        """
        构建 LangChain 工具列表。

        Args:
            user_id: 当前用户 ID。
            roadmap_id: 当前路线图 ID。
            concept_id: 当前概念 ID。

        Returns:
            list[Any]: 可供 ReAct 调用的工具列表。

        Raises:
            RuntimeError: 当工具加载失败时抛出。
        """

        from app.tools.mentor.get_concept_tutorial_tool import GetConceptTutorialTool
        from app.tools.mentor.get_roadmap_metadata_tool import GetRoadmapMetadataTool
        from app.tools.mentor.get_user_profile_tool import GetUserProfileTool
        from app.tools.mentor.mark_content_complete_tool import MarkContentCompleteTool

        base_tools = [
            GetConceptTutorialTool(),
            GetUserProfileTool(),
            GetRoadmapMetadataTool(),
            MarkContentCompleteTool(),
        ]

        langchain_tools: list[Any] = []

        for base_tool in base_tools:
            async def _tool_coroutine(
                _tool_name: str = base_tool.name,
                _base_tool: Any = base_tool,
                **kwargs: Any,
            ) -> dict[str, Any]:
                """
                工具协程包装器。

                Args:
                    _tool_name: 工具名称。
                    _base_tool: BaseTool 实例。
                    **kwargs: 模型输出的工具参数。

                Returns:
                    dict[str, Any]: 工具输出字典。

                Raises:
                    Exception: 当底层工具执行失败时抛出。
                """

                merged_args = self._inject_tool_context(
                    tool_name=_tool_name,
                    tool_args=kwargs,
                    user_id=user_id,
                    roadmap_id=roadmap_id,
                    concept_id=concept_id,
                )
                input_data = _base_tool.args_schema.model_validate(merged_args)
                output_data = await _base_tool.execute(input_data)
                return output_data.model_dump(exclude_none=True)

            tool = StructuredTool.from_function(
                coroutine=_tool_coroutine,
                name=base_tool.name,
                description=base_tool.description,
                args_schema=base_tool.args_schema,
            )
            langchain_tools.append(tool)

        # 为什么这样做：MCP 可能在某些环境不可用，失败时降级到内置工具可保证主链路稳定。
        try:
            mcp_tools = await load_context7_tools()
            if mcp_tools:
                langchain_tools.extend(mcp_tools)
                logger.info(
                    "mentor_mcp_tools_loaded",
                    tools_count=len(mcp_tools),
                    tools=[tool.name for tool in mcp_tools],
                )
        except Exception as exc:  # pragma: no cover - 兜底保护
            logger.warning(
                "mentor_mcp_tools_load_failed",
                error=str(exc),
            )

        return langchain_tools

    def _extract_text_chunks(self, chunk: Any) -> list[tuple[str, bool]]:
        """
        从 LangChain chunk 中提取文本与思考标记。

        Args:
            chunk: on_chat_model_stream 事件中的 chunk。

        Returns:
            list[tuple[str, bool]]: (文本, 是否思考内容) 列表。

        Raises:
            无。
        """

        extracted: list[tuple[str, bool]] = []
        raw_content = getattr(chunk, "content", None)

        if isinstance(raw_content, str):
            if raw_content:
                extracted.append((raw_content, False))
            return extracted

        if isinstance(raw_content, list):
            for item in raw_content:
                if isinstance(item, str):
                    if item:
                        extracted.append((item, False))
                    continue

                if isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if not text:
                        continue
                    is_thinking = bool(item.get("is_thinking")) or item.get("type") in {
                        "thinking",
                        "reasoning",
                        "reasoning_content",
                    }
                    extracted.append((str(text), is_thinking))

        additional_kwargs = getattr(chunk, "additional_kwargs", {}) or {}
        reasoning_text = additional_kwargs.get("reasoning_content")
        if isinstance(reasoning_text, str) and reasoning_text:
            extracted.append((reasoning_text, True))

        return extracted

    def _to_jsonable(self, value: Any) -> Any:
        """
        将任意对象转换为可 JSON 序列化的结构。

        Args:
            value: 待转换对象。

        Returns:
            Any: 可序列化对象。

        Raises:
            无。
        """

        try:
            return jsonable_encoder(value)
        except Exception:  # pragma: no cover - 兜底转换
            return str(value)

    def _try_parse_json_text(self, value: Any) -> Any:
        """
        尝试将字符串解析为 JSON 对象。

        Args:
            value: 待解析值。

        Returns:
            Any: 解析成功返回对象，否则返回原值。
        """
        if not isinstance(value, str):
            return value
        text = value.strip()
        if not text:
            return value
        if not ((text.startswith("{") and text.endswith("}")) or (text.startswith("[") and text.endswith("]"))):
            return value
        try:
            import json
            return json.loads(text)
        except Exception:
            return value

    def _normalize_tool_result(self, raw_output: Any) -> Any:
        """
        规范化工具输出，避免将 ToolMessage 包装结构直接暴露给前端。

        Args:
            raw_output: LangGraph 工具事件输出。

        Returns:
            Any: 规范化后的工具结果。
        """
        jsonable_output = self._to_jsonable(raw_output)
        if isinstance(jsonable_output, dict):
            if jsonable_output.get("type") == "tool" and "content" in jsonable_output:
                return self._try_parse_json_text(jsonable_output.get("content"))
            if "content" in jsonable_output and len(jsonable_output.keys()) == 1:
                return self._try_parse_json_text(jsonable_output.get("content"))
        return jsonable_output

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        agent_mode: str,
        model_name: MentorModelName,
        user_id: str,
        roadmap_id: str,
        concept_id: str | None,
        roadmap_title: str,
        current_concept: str | None,
        user_background: str | None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        执行流式对话并产出结构化事件。

        Args:
            messages: 历史对话消息列表。
            agent_mode: Agent 模式（companion/tutoring）。
            model_name: 模型名称（qwen 系列）。
            user_id: 当前用户 ID。
            roadmap_id: 当前路线图 ID。
            concept_id: 当前概念 ID。
            roadmap_title: 路线图标题。
            current_concept: 当前概念名称。
            user_background: 用户背景。

        Returns:
            AsyncGenerator[dict[str, Any], None]: SSE 事件字典流。

        Raises:
            ValueError: 当 agent_mode 不合法时抛出。
        """

        system_prompt = self._build_system_prompt(
            agent_mode=agent_mode,
            roadmap_title=roadmap_title,
            current_concept=current_concept,
            user_background=user_background,
        )
        tools = await self._build_langchain_tools(
            user_id=user_id,
            roadmap_id=roadmap_id,
            concept_id=concept_id,
        )

        llm = self._create_llm(model_name_override=model_name)
        graph = create_react_agent(
            model=llm,
            tools=tools,
            prompt=system_prompt,
        )

        input_messages: list[HumanMessage | AIMessage] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            if not content:
                continue
            if role == "assistant":
                input_messages.append(AIMessage(content=content))
            else:
                input_messages.append(HumanMessage(content=content))

        async for event in graph.astream_events({"messages": input_messages}, version="v2"):
            event_kind = event.get("event")

            if event_kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if not chunk:
                    continue
                for text, is_thinking in self._extract_text_chunks(chunk):
                    payload: dict[str, Any] = {
                        "type": "text_delta",
                        "content": text,
                    }
                    if is_thinking:
                        payload["is_thinking"] = True
                    yield payload

            elif event_kind == "on_tool_start":
                yield {
                    "type": "tool_call_start",
                    "tool_call_id": event.get("run_id", ""),
                    "tool_name": event.get("name", ""),
                    "args": self._to_jsonable(event.get("data", {}).get("input", {})),
                }

            elif event_kind == "on_tool_end":
                yield {
                    "type": "tool_call_end",
                    "tool_call_id": event.get("run_id", ""),
                    "tool_name": event.get("name", ""),
                    "success": True,
                    "result": self._normalize_tool_result(event.get("data", {}).get("output", {})),
                }

