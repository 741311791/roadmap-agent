"""
MCP 工具加载器（使用官方 langchain-mcp-adapters）
"""
import asyncio
import json
from pathlib import Path
from typing import List

import structlog
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import BaseTool

logger = structlog.get_logger()
_context7_tools_cache: List[BaseTool] | None = None
_context7_tools_lock = asyncio.Lock()


async def load_context7_tools() -> List[BaseTool]:
    """
    使用官方 langchain-mcp-adapters 加载 Context7 工具
    
    返回的工具：
    - resolve-library-id: 解析技术库的 Context7 ID
    - query-docs: 查询官方技术文档
    
    Returns:
        LangChain 兼容的工具列表
        
    Raises:
        FileNotFoundError: 如果 mcp_servers.json 不存在
        ValueError: 如果 context7 配置无效
    """
    global _context7_tools_cache

    if _context7_tools_cache is not None:
        logger.debug(
            "context7_tools_cache_hit",
            tools_count=len(_context7_tools_cache),
        )
        return _context7_tools_cache

    async with _context7_tools_lock:
        if _context7_tools_cache is not None:
            logger.debug(
                "context7_tools_cache_hit_after_wait",
                tools_count=len(_context7_tools_cache),
            )
            return _context7_tools_cache

        config_path = Path("mcp_servers.json")
        if not config_path.exists():
            logger.warning("mcp_servers_json_not_found")
            _context7_tools_cache = []
            return _context7_tools_cache

        with open(config_path, "r", encoding="utf-8") as file_obj:
            config = json.load(file_obj)

        context7_config = next(
            (
                server
                for server in config.get("servers", [])
                if server.get("name") == "context7" and server.get("enabled")
            ),
            None,
        )

        if not context7_config:
            logger.warning("context7_mcp_not_configured_or_disabled")
            _context7_tools_cache = []
            return _context7_tools_cache

        try:
            client = MultiServerMCPClient(
                {
                    "context7": {
                        "transport": "stdio",
                        "command": context7_config["command"],
                        "args": context7_config["args"],
                    }
                }
            )
            _context7_tools_cache = await client.get_tools()

            logger.info(
                "context7_tools_loaded",
                tools_count=len(_context7_tools_cache),
                tools=[tool.name for tool in _context7_tools_cache],
            )
            return _context7_tools_cache
        except Exception as exc:
            logger.error(
                "context7_tools_loading_failed",
                error=str(exc),
                exc_info=True,
            )
            _context7_tools_cache = []
            return _context7_tools_cache

