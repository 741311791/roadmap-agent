"""
Curriculum Architect Agent 测试
"""

import pytest

from app.agents.curriculum_architect import CurriculumArchitectAgent


class _DummySearchResult:
    """
    模拟 web_search 返回结果
    """

    def __init__(self, results: list[dict[str, str]]):
        self.results = results


class _DummyFetchResult:
    """
    模拟 web_fetch 返回结果
    """

    def __init__(self, content: str):
        self.content = content


class _DummyToolRegistry:
    """
    用于验证工具调用顺序的轻量级 ToolRegistry
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def execute_tool(self, name: str, arguments: dict, **kwargs):
        self.calls.append((name, arguments))

        if name == "web_search":
            return _DummySearchResult(
                [
                    {
                        "title": "React Docs - Learn React",
                        "url": "https://react.dev/learn",
                        "snippet": "Official React learning materials and learning path.",
                    }
                ]
            )

        if name == "web_fetch":
            return _DummyFetchResult(
                "Start with components, props, state, and effects before moving to production patterns."
            )

        raise AssertionError(f"Unexpected tool call: {name}")


@pytest.mark.asyncio
async def test_collect_external_references_uses_web_search_and_web_fetch():
    """
    应该通过 web_search 和 web_fetch 生成可注入 Prompt 的参考摘要
    """
    tool_registry = _DummyToolRegistry()
    agent = CurriculumArchitectAgent(
        agent_id="curriculum_architect_test",
        tool_registry=tool_registry,
    )

    references_text = await agent._collect_external_references(
        {
            "parsed_goal": "Become a React frontend engineer",
            "user_goal": "Learn React deeply",
            "key_technologies": ["React", "TypeScript"],
            "primary_language": "en",
        }
    )

    assert "React Docs - Learn React" in references_text
    assert "https://react.dev/learn" in references_text
    assert "Start with components, props, state" in references_text
    assert tool_registry.calls[0][0] == "web_search"
    assert any(call[0] == "web_fetch" for call in tool_registry.calls)


def test_resolve_authoritative_domains_prefers_official_sites():
    """
    应该为常见技术栈返回官方站点域名
    """
    agent = CurriculumArchitectAgent(agent_id="curriculum_architect_test")

    domains = agent._resolve_authoritative_domains(
        ["React", "Next.js", "TypeScript"]
    )

    assert "react.dev" in domains
    assert "nextjs.org" in domains
    assert "typescriptlang.org" in domains
