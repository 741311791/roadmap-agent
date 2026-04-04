"""
Context7 文档查询工具

职责：
- 为 Mentor Agent 提供最新官方文档与代码示例查询能力
- 在内部串联 resolve-library-id 与 query-docs 两个 MCP 工具
- 对外暴露单个稳定的 web-like 工具接口，避免模型直接感知 MCP 细节
"""
import re
from typing import Any

import structlog
from pydantic import BaseModel, Field

from app.tools.base import BaseTool
from app.tools.mcp_loader import load_context7_tools

logger = structlog.get_logger()

LIBRARY_ID_PATTERN = re.compile(r"/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)?")


class Context7DocsQuery(BaseModel):
    """
    Context7 文档查询输入
    """

    library_name: str = Field(..., min_length=1, description="需要查询的库或框架名称")
    query: str = Field(..., min_length=1, description="具体想查的 API、概念或用法问题")


class Context7DocsResult(BaseModel):
    """
    Context7 文档查询输出
    """

    library_id: str = Field(..., description="解析出的 Context7 兼容库 ID")
    content: str = Field(..., description="查询到的文档内容与代码示例")


class Context7DocsTool(BaseTool[Context7DocsQuery, Context7DocsResult]):
    """
    将 Context7 的两步调用封装成单个 Mentor 可用工具
    """

    def __init__(self) -> None:
        """
        初始化 Context7 文档工具
        """
        super().__init__(
            tool_id="context7_docs_v1",
            name="context7_docs",
            description=(
                "Retrieve up-to-date documentation and code examples for a specific "
                "library or framework. Use this when the user asks about APIs, hooks, "
                "framework patterns, or library-specific implementation details."
            ),
            args_schema=Context7DocsQuery,
        )

    @classmethod
    def _extract_library_id(cls, value: Any) -> str | None:
        """
        从 Context7 resolve 返回值中提取 library ID
        """
        if isinstance(value, str):
            matched = LIBRARY_ID_PATTERN.search(value)
            return matched.group(0) if matched else None

        if isinstance(value, dict):
            for key in ("libraryId", "library_id", "id"):
                candidate = value.get(key)
                extracted = cls._extract_library_id(candidate)
                if extracted:
                    return extracted
            for nested_value in value.values():
                extracted = cls._extract_library_id(nested_value)
                if extracted:
                    return extracted
            return None

        if isinstance(value, list):
            for item in value:
                extracted = cls._extract_library_id(item)
                if extracted:
                    return extracted
            return None

        return None

    async def execute(self, input_data: Context7DocsQuery, **kwargs) -> Context7DocsResult:
        """
        查询最新官方文档

        Args:
            input_data: 工具输入参数

        Returns:
            文档内容与最终使用的库 ID

        Raises:
            ValueError: 当 Context7 不可用、无法解析库 ID 或查询失败时抛出
        """
        loaded_tools = await load_context7_tools()
        if not loaded_tools:
            raise ValueError("Context7 当前不可用，请稍后再试。")

        tool_map = {tool.name: tool for tool in loaded_tools}
        resolve_tool = tool_map.get("resolve-library-id")
        query_tool = tool_map.get("query-docs")
        if resolve_tool is None or query_tool is None:
            raise ValueError("Context7 工具未正确加载，缺少 resolve 或 query 能力。")

        resolve_result = await resolve_tool.ainvoke(
            {
                "query": input_data.query,
                "libraryName": input_data.library_name,
            }
        )
        library_id = self._extract_library_id(resolve_result)
        if not library_id:
            raise ValueError("Context7 未能解析出有效的库 ID，请换一个更明确的库名。")

        docs_result = await query_tool.ainvoke(
            {
                "libraryId": library_id,
                "query": input_data.query,
            }
        )
        docs_content = docs_result if isinstance(docs_result, str) else str(docs_result)
        logger.info(
            "context7_docs_success",
            library_name=input_data.library_name,
            library_id=library_id,
        )
        return Context7DocsResult(
            library_id=library_id,
            content=docs_content,
        )
