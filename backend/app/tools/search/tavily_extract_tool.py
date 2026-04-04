"""
Tavily Extract 工具

职责：
- 使用 Tavily Extract API 抓取指定 URL 的正文内容
- 复用项目内现有的 Tavily 速率限制与 Key 缓存
- 输出适合 Mentor Agent 后续推理的页面正文摘要
"""
from typing import Literal

import httpx
import structlog
from pydantic import BaseModel, Field

from app.core.rate_limiter import get_rate_limiter
from app.core.tavily_key_cache import get_tavily_key_cache
from app.tools.base import BaseTool

logger = structlog.get_logger()


class WebFetchQuery(BaseModel):
    """
    web_fetch 工具输入
    """

    url: str = Field(..., description="需要抓取正文的完整 URL")
    extract_depth: Literal["basic", "advanced"] = Field(
        default="basic",
        description="抽取深度：basic 或 advanced",
    )
    format: Literal["markdown", "text"] = Field(
        default="markdown",
        description="返回内容格式：markdown 或 text",
    )
    include_images: bool = Field(default=False, description="是否返回页面图片列表")
    timeout: float | None = Field(
        default=20.0,
        ge=1.0,
        le=60.0,
        description="Tavily Extract 请求超时时间（秒）",
    )


class WebFetchResult(BaseModel):
    """
    web_fetch 工具输出
    """

    url: str = Field(..., description="抓取来源 URL")
    content: str = Field(..., description="抽取后的正文内容")
    images: list[str] = Field(default_factory=list, description="页面图片 URL 列表")
    response_time: float | None = Field(None, description="接口响应耗时（秒）")
    request_id: str | None = Field(None, description="Tavily 请求 ID")


class TavilyExtractTool(BaseTool[WebFetchQuery, WebFetchResult]):
    """
    基于 Tavily Extract API 的网页抓取工具
    """

    def __init__(self) -> None:
        """
        初始化 Tavily Extract 工具
        """
        super().__init__(
            tool_id="tavily_extract_v1",
            name="web_fetch",
            description=(
                "Fetch the full content of a specific URL. "
                "Use this after web_search when you already have a target page and need "
                "the page body, official docs, article text, or detailed reference content."
            ),
            args_schema=WebFetchQuery,
        )
        self._http_client = httpx.AsyncClient(
            base_url="https://api.tavily.com",
            timeout=httpx.Timeout(60.0),
        )

    async def _resolve_api_key(self, pre_allocated_tavily_key: str | None = None) -> str:
        """
        获取可用的 Tavily API Key
        """
        if pre_allocated_tavily_key:
            return pre_allocated_tavily_key

        key_cache = get_tavily_key_cache()
        api_key = await key_cache.get_random_key()
        if not api_key:
            raise ValueError("当前没有可用的 Tavily API Key，暂时无法执行网页抓取。")
        return api_key

    async def execute(
        self,
        input_data: WebFetchQuery,
        pre_allocated_tavily_key: str | None = None,
    ) -> WebFetchResult:
        """
        执行网页正文抓取

        Args:
            input_data: 工具输入参数
            pre_allocated_tavily_key: 预分配的 Tavily API Key

        Returns:
            抽取后的网页正文

        Raises:
            ValueError: 当 URL 不合法、无可用 Key 或 Tavily 返回错误时抛出
        """
        normalized_url = input_data.url.strip()
        if not normalized_url.startswith(("https://", "http://")):
            raise ValueError("web_fetch 需要传入完整的 http/https URL。")

        api_key = await self._resolve_api_key(pre_allocated_tavily_key)
        rate_limiter = get_rate_limiter()
        key_cache = get_tavily_key_cache()

        payload = {
            "urls": normalized_url,
            "extract_depth": input_data.extract_depth,
            "format": input_data.format,
            "include_images": input_data.include_images,
        }
        if input_data.timeout is not None:
            payload["timeout"] = input_data.timeout

        await rate_limiter.acquire("tavily")
        response = await self._http_client.post(
            "/extract",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

        if response.status_code == 401:
            await key_cache.evict_key(api_key)
            raise ValueError("Tavily API Key 无效，已自动移出缓存。")

        if response.status_code >= 400:
            error_payload = response.json() if response.content else {}
            detail = error_payload.get("detail", {})
            error_message = detail.get("error") or response.text
            raise ValueError(f"Tavily Extract 请求失败：{error_message}")

        response_data = response.json()
        results = response_data.get("results", [])
        failed_results = response_data.get("failed_results", [])

        if not results:
            first_failure = failed_results[0] if failed_results else {}
            raise ValueError(
                first_failure.get("error")
                or "Tavily Extract 没有返回可用的页面内容。"
            )

        first_result = results[0]
        raw_content = (first_result.get("raw_content") or "").strip()
        if not raw_content:
            raise ValueError("Tavily Extract 返回成功，但页面正文为空。")

        await key_cache.update_quota(api_key, used_count=1)
        logger.info(
            "tavily_extract_success",
            url=normalized_url,
            response_time=response_data.get("response_time"),
            request_id=response_data.get("request_id"),
        )

        return WebFetchResult(
            url=first_result.get("url") or normalized_url,
            content=raw_content,
            images=first_result.get("images") or [],
            response_time=response_data.get("response_time"),
            request_id=response_data.get("request_id"),
        )
