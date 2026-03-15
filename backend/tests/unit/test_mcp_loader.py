from types import SimpleNamespace

import pytest

from app.tools import mcp_loader


@pytest.mark.asyncio
async def test_load_context7_tools_uses_cache(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """测试 Context7 工具会命中进程级缓存"""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(mcp_loader, "_context7_tools_cache", None)

    config_path = tmp_path / "mcp_servers.json"
    config_path.write_text(
        (
            '{"servers":[{"name":"context7","enabled":true,'
            '"command":"context7","args":["serve"]}]}'
        ),
        encoding="utf-8",
    )

    class FakeMultiServerMCPClient:
        """模拟 MCP 客户端"""

        init_count = 0
        get_tools_count = 0

        def __init__(self, _config) -> None:
            FakeMultiServerMCPClient.init_count += 1

        async def get_tools(self):
            FakeMultiServerMCPClient.get_tools_count += 1
            return [SimpleNamespace(name="query-docs")]

    monkeypatch.setattr(mcp_loader, "MultiServerMCPClient", FakeMultiServerMCPClient)

    first_tools = await mcp_loader.load_context7_tools()
    second_tools = await mcp_loader.load_context7_tools()

    assert len(first_tools) == 1
    assert first_tools is second_tools
    assert FakeMultiServerMCPClient.init_count == 1
    assert FakeMultiServerMCPClient.get_tools_count == 1
