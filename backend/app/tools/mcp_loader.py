"""
MCP 工具加载器（使用官方 langchain-mcp-adapters）
"""
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.tools import BaseTool
from typing import List
import structlog
import json
from pathlib import Path

logger = structlog.get_logger()


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
    # 读取 MCP 配置
    config_path = Path("mcp_servers.json")
    if not config_path.exists():
        logger.warning("mcp_servers_json_not_found")
        return []
    
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # 查找 context7 配置
    context7_config = next(
        (s for s in config.get("servers", []) 
         if s.get("name") == "context7" and s.get("enabled")),
        None
    )
    
    if not context7_config:
        logger.warning("context7_mcp_not_configured_or_disabled")
        return []
    
    try:
        # 使用官方适配器连接 MCP Server
        client = MultiServerMCPClient({
            "context7": {
                "transport": "stdio",
                "command": context7_config["command"],
                "args": context7_config["args"]
            }
        })
        
        # 自动加载所有工具（官方适配器处理所有细节）
        tools = await client.get_tools()
        
        logger.info(
            "context7_tools_loaded",
            tools_count=len(tools),
            tools=[t.name for t in tools]
        )
        
        return tools
        
    except Exception as e:
        logger.error(
            "context7_tools_loading_failed",
            error=str(e),
            exc_info=True
        )
        return []

