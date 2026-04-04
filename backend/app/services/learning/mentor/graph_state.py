"""
答疑 Agent 图运行状态
"""

from typing import TypedDict


class MentorThreadState(TypedDict, total=False):
    """
    答疑 Agent 的轻量运行状态
    """

    user_message: str
    qa_style: str
    emotion_label: str
    session_id: str
    trace_id: str
