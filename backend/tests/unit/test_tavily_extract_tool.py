from unittest.mock import AsyncMock

import pytest

from app.tools.search.tavily_extract_tool import TavilyExtractTool, WebFetchQuery


@pytest.mark.asyncio
async def test_web_fetch_returns_extracted_content(monkeypatch) -> None:
    """web_fetch 应返回 Tavily Extract 抽取出的正文内容。"""
    tool = TavilyExtractTool()

    class _FakeResponse:
        status_code = 200
        content = b'{"ok": true}'

        @staticmethod
        def json() -> dict:
            return {
                "results": [
                    {
                        "url": "https://example.com/docs",
                        "raw_content": "Example documentation content",
                        "images": ["https://example.com/image.png"],
                    }
                ],
                "response_time": 0.42,
                "request_id": "req-1",
            }

    fake_rate_limiter = type(
        "FakeRateLimiter",
        (),
        {
            "acquire": AsyncMock(),
        },
    )()
    fake_key_cache = type(
        "FakeKeyCache",
        (),
        {
            "get_random_key": AsyncMock(return_value="tvly-test-key"),
            "update_quota": AsyncMock(),
            "evict_key": AsyncMock(),
        },
    )()

    from app.tools.search import tavily_extract_tool as module

    monkeypatch.setattr(module, "get_rate_limiter", lambda: fake_rate_limiter)
    monkeypatch.setattr(module, "get_tavily_key_cache", lambda: fake_key_cache)
    tool._http_client.post = AsyncMock(return_value=_FakeResponse())

    result = await tool.execute(WebFetchQuery(url="https://example.com/docs"))

    assert result.url == "https://example.com/docs"
    assert result.content == "Example documentation content"
    assert result.images == ["https://example.com/image.png"]
    fake_rate_limiter.acquire.assert_awaited_once_with("tavily")
    fake_key_cache.update_quota.assert_awaited_once_with("tvly-test-key", used_count=1)


@pytest.mark.asyncio
async def test_web_fetch_rejects_non_http_url() -> None:
    """web_fetch 应拒绝不完整的 URL 输入。"""
    tool = TavilyExtractTool()

    with pytest.raises(ValueError, match="http/https URL"):
        await tool.execute(WebFetchQuery(url="example.com/docs"))
