"""
工作流执行器耗时解析单元测试
"""

from app.core.orchestrator.base import INTERNAL_NODE_DURATION_MS_KEY
from app.core.orchestrator.executor import (
    _resolve_node_duration_ms,
    _split_node_output_and_internal_duration,
)


def test_split_node_output_and_internal_duration_should_strip_internal_key():
    """
    测试节点输出拆分时应移除内部耗时字段

    Returns:
        None
    """
    output, duration_ms = _split_node_output_and_internal_duration(
        {
            "current_step": "curriculum_design",
            INTERNAL_NODE_DURATION_MS_KEY: 12345,
        }
    )

    assert output == {"current_step": "curriculum_design"}
    assert duration_ms == 12345


def test_resolve_node_duration_should_use_fallback_when_start_missing():
    """
    测试缺少开始事件时应使用节点内部耗时兜底

    Returns:
        None
    """
    duration_ms = _resolve_node_duration_ms(
        start_time=None,
        current_time=20.0,
        fallback_duration_ms=9876,
    )

    assert duration_ms == 9876


def test_resolve_node_duration_should_prefer_larger_internal_duration():
    """
    测试事件耗时偏小时应采用更可信的内部耗时

    Returns:
        None
    """
    duration_ms = _resolve_node_duration_ms(
        start_time=10.0,
        current_time=10.15,
        fallback_duration_ms=18234,
    )

    assert duration_ms == 18234
