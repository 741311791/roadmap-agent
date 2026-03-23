from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.learning.mentor_context_service import MentorContextService
from app.services.learning.memory_service import MemoryService, MentorMemoryFact
from app.utils.serializers import fast_dumps


@pytest.mark.asyncio
async def test_get_short_term_messages_reverses_cached_order(monkeypatch) -> None:
    """Redis 中按最新优先存储时，读取后应恢复为对话顺序。"""
    service = MentorContextService(memory_service=AsyncMock())

    cached_items = [
        fast_dumps({"role": "assistant", "content": "第二条"}).decode("utf-8"),
        fast_dumps({"role": "user", "content": "第一条"}).decode("utf-8"),
    ]

    fake_client = SimpleNamespace(lrange=AsyncMock(return_value=cached_items))

    from app.services.learning import mentor_context_service as module

    monkeypatch.setattr(module.redis_client, "connect", AsyncMock())
    monkeypatch.setattr(module.redis_client, "_client", fake_client)

    messages = await service.get_short_term_messages(AsyncMock(), session_id="session-1")

    assert [item["content"] for item in messages] == ["第一条", "第二条"]


@pytest.mark.asyncio
async def test_rebuild_short_term_messages_uses_recent_db_messages(monkeypatch) -> None:
    """Cache miss 回补时应读取数据库最近消息并回写缓存。"""
    service = MentorContextService(memory_service=AsyncMock())

    db_messages = [
        SimpleNamespace(
            message_id="m-1",
            role="user",
            content="你好",
            created_at=SimpleNamespace(isoformat=lambda: "2026-03-22T00:00:00"),
        ),
        SimpleNamespace(
            message_id="m-2",
            role="assistant",
            content="你好，请问我可以帮你什么？",
            created_at=SimpleNamespace(isoformat=lambda: "2026-03-22T00:00:01"),
        ),
    ]

    from app.services.learning import mentor_context_service as module

    monkeypatch.setattr(module.chat_message_crud, "get_recent_messages", AsyncMock(return_value=db_messages))
    replace_mock = AsyncMock()
    monkeypatch.setattr(service, "replace_short_term_messages", replace_mock)

    rebuilt_messages = await service.rebuild_short_term_messages(AsyncMock(), session_id="session-2")

    assert [item["message_id"] for item in rebuilt_messages] == ["m-1", "m-2"]
    replace_mock.assert_awaited_once()


def test_parse_memory_content_reads_explicit_type_tag() -> None:
    """显式类型标签应被正确解析并去除前缀。"""
    memory_type, content = MemoryService.parse_memory_content(
        "[misconception] 用户经常混淆布局阶段和合成阶段"
    )

    assert memory_type == "misconception"
    assert content == "用户经常混淆布局阶段和合成阶段"


def test_build_long_term_memory_summary_groups_by_type() -> None:
    """长期记忆应整理为按类型分组的 Prompt 摘要。"""
    facts = [
        MentorMemoryFact(memory_type="progress", content="用户当前已经能稳定区分布局阶段和合成阶段"),
        MentorMemoryFact(memory_type="misconception", content="用户经常混淆布局阶段和合成阶段"),
        MentorMemoryFact(memory_type="preference", content="用户偏好苏格拉底式提问引导"),
        MentorMemoryFact(memory_type="goal", content="用户本周的学习目标是优先搞清布局和合成的区别"),
    ]

    summary_lines = MentorContextService.build_long_term_memory_summary(facts)

    assert summary_lines == [
        "学习偏好：用户偏好苏格拉底式提问引导",
        "当前目标：用户本周的学习目标是优先搞清布局和合成的区别",
        "历史误区：用户经常混淆布局阶段和合成阶段",
        "当前进展：用户当前已经能稳定区分布局阶段和合成阶段",
    ]


def test_build_long_term_memory_sections_groups_into_fixed_sections() -> None:
    """长期记忆应拆分为固定小节，便于 Prompt 稳定注入。"""
    facts = [
        MentorMemoryFact(memory_type="progress", content="用户当前已经能稳定区分布局阶段和合成阶段"),
        MentorMemoryFact(memory_type="misconception", content="用户经常混淆布局阶段和合成阶段"),
        MentorMemoryFact(memory_type="preference", content="用户偏好苏格拉底式提问引导"),
        MentorMemoryFact(memory_type="goal", content="用户本周的学习目标是优先搞清布局和合成的区别"),
        MentorMemoryFact(memory_type="other", content="用户最近开始关注渲染性能"),
    ]

    sections = MentorContextService.build_long_term_memory_sections(facts)

    assert sections == {
        "preferences": ["用户偏好苏格拉底式提问引导"],
        "goals": ["用户本周的学习目标是优先搞清布局和合成的区别"],
        "misconceptions": ["用户经常混淆布局阶段和合成阶段"],
        "progress": ["用户当前已经能稳定区分布局阶段和合成阶段"],
        "other_facts": ["用户最近开始关注渲染性能"],
    }
