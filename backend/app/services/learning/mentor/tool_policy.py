"""
答疑 Agent 工具策略
"""

import re
from typing import Any

from app.services.learning.mentor.event_types import MentorQaAgentInput

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
EXPLICIT_WEB_SEARCH_PATTERN = re.compile(
    r"(搜索|搜一下|帮我搜|查一下|联网|上网|互联网|web search|search the web|google一下|google it)",
    re.IGNORECASE,
)
RECENCY_PATTERN = re.compile(
    r"(最新|最近|当前|近日|近期|截至今天|截至目前|到今天|今年|本月|本周|latest|current|recent|today|this year|up[- ]to[- ]date)",
    re.IGNORECASE,
)


class MentorToolPolicy:
    """
    答疑 Agent 的工具选择与参数补全策略
    """

    def __init__(self, *, allowed_tool_names: list[str] | None = None) -> None:
        self._allowed_tool_names = allowed_tool_names or [
            "web_search",
            "web_fetch",
            "context7_docs",
        ]

    def get_allowed_tool_names(self) -> list[str]:
        """
        返回允许暴露给答疑 Agent 的工具列表
        """

        return list(self._allowed_tool_names)

    @staticmethod
    def requires_external_search(user_message: str) -> bool:
        """
        判断用户是否明确要求联网或索取最新外部信息
        """

        normalized_message = user_message.strip()
        if not normalized_message:
            return False
        return bool(
            EXPLICIT_WEB_SEARCH_PATTERN.search(normalized_message)
            or RECENCY_PATTERN.search(normalized_message)
        )

    @staticmethod
    def contains_url(user_message: str) -> bool:
        """
        判断用户消息中是否包含 URL
        """

        return bool(URL_PATTERN.search(user_message))

    def resolve_forced_tool(self, input_data: MentorQaAgentInput) -> str | None:
        """
        为首轮请求选择更稳妥的强制工具
        """

        user_message = input_data.user_message
        allowed_tool_names = set(self._allowed_tool_names)

        if "web_fetch" in allowed_tool_names and self.contains_url(user_message):
            return "web_fetch"

        if "web_search" in allowed_tool_names and self.requires_external_search(user_message):
            return "web_search"

        return None

    def enrich_tool_arguments(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        input_data: MentorQaAgentInput,
    ) -> dict[str, Any]:
        """
        在不改变工具契约的前提下补齐常见默认参数
        """

        if tool_name != "web_search":
            return dict(arguments)

        normalized_arguments = dict(arguments)
        user_message = input_data.user_message.strip()

        if not normalized_arguments.get("query"):
            normalized_arguments["query"] = user_message

        if self.requires_external_search(user_message):
            normalized_arguments.setdefault("search_depth", "advanced")
            normalized_arguments.setdefault("time_range", "year")
            if int(normalized_arguments.get("max_results") or 0) < 8:
                normalized_arguments["max_results"] = 8

        return normalized_arguments
