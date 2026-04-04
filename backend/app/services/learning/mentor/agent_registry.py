"""
Mentor Agent 静态注册表
"""

from app.services.learning.mentor.event_types import MentorAgentKind

MENTOR_AGENT_KINDS: tuple[MentorAgentKind, ...] = ("qa", "guide", "quiz")


class MentorAgentRegistry:
    """
    管理聊天页面固定 Tab 与 Agent 的静态映射
    """

    @staticmethod
    def list_kinds() -> tuple[MentorAgentKind, ...]:
        """
        返回当前支持的 Agent 类型
        """

        return MENTOR_AGENT_KINDS

    @staticmethod
    def is_supported(kind: str) -> bool:
        """
        判断 Agent 类型是否受支持
        """

        return kind in MENTOR_AGENT_KINDS
