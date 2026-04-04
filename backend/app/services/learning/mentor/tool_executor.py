"""
答疑 Agent 工具执行器
"""

import json
from typing import Any, Awaitable, Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from app.tools.registry import ToolRegistry

MAX_TOOL_RESULT_CHARS = 12_000


class MentorToolExecutor:
    """
    将现有 ToolRegistry 适配为 LangChain 可调用工具
    """

    def __init__(self, tool_registry: ToolRegistry | None) -> None:
        self._tool_registry = tool_registry

    @staticmethod
    def serialize_tool_result(result: Any) -> str:
        """
        将工具结果序列化为传回模型的文本
        """

        if isinstance(result, BaseModel):
            payload: Any = result.model_dump()
        elif hasattr(result, "model_dump"):
            payload = result.model_dump()
        else:
            payload = result

        if isinstance(payload, str):
            serialized = payload
        else:
            serialized = json.dumps(payload, ensure_ascii=False, default=str)

        if len(serialized) <= MAX_TOOL_RESULT_CHARS:
            return serialized
        return f"{serialized[:MAX_TOOL_RESULT_CHARS]}...(truncated)"

    @staticmethod
    def is_error_result(serialized_result: str) -> bool:
        """
        判断工具结果是否为错误结果
        """

        return serialized_result.startswith("\"Error") or serialized_result.startswith("Error")

    async def execute_tool(self, *, name: str, arguments: dict[str, Any]) -> str:
        """
        执行工具并返回序列化结果
        """

        if self._tool_registry is None:
            return f"Error: tool registry is not configured for '{name}'."

        result = await self._tool_registry.execute_tool(name=name, arguments=arguments)
        return self.serialize_tool_result(result)

    def build_langchain_tools(
        self,
        *,
        allowed_tool_names: list[str],
        argument_enricher: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> list[StructuredTool]:
        """
        将允许的项目工具转换为 LangChain StructuredTool
        """

        if self._tool_registry is None:
            return []

        structured_tools: list[StructuredTool] = []

        for tool_name in allowed_tool_names:
            tool = self._tool_registry.get_tool(tool_name)
            if tool is None:
                continue

            async def _run_tool(
                _tool_name: str = tool_name,
                _enricher: Callable[[str, dict[str, Any]], dict[str, Any]] | None = argument_enricher,
                **kwargs: Any,
            ) -> str:
                normalized_arguments = dict(kwargs)
                if _enricher is not None:
                    normalized_arguments = _enricher(_tool_name, normalized_arguments)
                return await self.execute_tool(
                    name=_tool_name,
                    arguments=normalized_arguments,
                )

            structured_tools.append(
                StructuredTool.from_function(
                    coroutine=_run_tool,
                    name=tool.name,
                    description=tool.description,
                    args_schema=tool.args_schema,
                )
            )

        return structured_tools
