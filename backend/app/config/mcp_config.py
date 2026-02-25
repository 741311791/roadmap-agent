"""
MCP (Model Context Protocol) 配置管理

职责：
- 管理 MCP Server 连接配置
- 支持从配置文件或环境变量加载
- 提供默认的 MCP Server 配置

配置示例 (mcp_servers.json):
```json
{
  "servers": [
    {
      "name": "filesystem",
      "description": "File system operations",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "enabled": true
    },
    {
      "name": "github",
      "description": "GitHub API integration",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "enabled": false
    }
  ]
}
```
"""
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
import json
from pathlib import Path
import structlog

logger = structlog.get_logger()


class MCPServerConfig(BaseModel):
    """
    MCP Server 配置
    
    定义单个 MCP Server 的连接参数
    """
    name: str = Field(..., description="Server 名称（唯一标识符）")
    description: str = Field("", description="Server 功能描述")
    command: str = Field(..., description="启动命令（如 'npx'）")
    args: List[str] = Field(default_factory=list, description="命令参数")
    enabled: bool = Field(True, description="是否启用此 Server")
    env: Optional[Dict[str, str]] = Field(None, description="环境变量（可选）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "filesystem",
                "description": "File system operations",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem"],
                "enabled": True
            }
        }


class MCPServersConfig(BaseModel):
    """
    MCP Servers 配置集合
    
    管理多个 MCP Server 的配置
    """
    servers: List[MCPServerConfig] = Field(
        default_factory=list,
        description="MCP Server 配置列表"
    )
    
    def get_enabled_servers(self) -> List[MCPServerConfig]:
        """获取所有已启用的 MCP Server 配置"""
        return [s for s in self.servers if s.enabled]
    
    def get_server_by_name(self, name: str) -> Optional[MCPServerConfig]:
        """根据名称查找 MCP Server 配置"""
        for server in self.servers:
            if server.name == name:
                return server
        return None


# ============================================================
# 默认 MCP Server 配置
# ============================================================

DEFAULT_MCP_SERVERS = MCPServersConfig(
    servers=[
        # 示例：文件系统工具
        # MCPServerConfig(
        #     name="filesystem",
        #     description="File system operations (read, write, list files)",
        #     command="npx",
        #     args=["-y", "@modelcontextprotocol/server-filesystem"],
        #     enabled=False,  # 默认禁用，需要用户手动启用
        # ),
        
        # 示例：GitHub 集成
        # MCPServerConfig(
        #     name="github",
        #     description="GitHub API integration",
        #     command="npx",
        #     args=["-y", "@modelcontextprotocol/server-github"],
        #     enabled=False,
        # ),
        
        # 示例：Google Drive 集成
        # MCPServerConfig(
        #     name="gdrive",
        #     description="Google Drive integration",
        #     command="npx",
        #     args=["-y", "@modelcontextprotocol/server-gdrive"],
        #     enabled=False,
        # ),
    ]
)


# ============================================================
# 配置加载函数
# ============================================================

def load_mcp_config(config_path: Optional[Path] = None) -> MCPServersConfig:
    """
    加载 MCP Server 配置
    
    Args:
        config_path: 配置文件路径（可选）
                    如果不提供，依次尝试：
                    1. 当前目录 ./mcp_servers.json
                    2. backend 目录 backend/mcp_servers.json
                    3. 使用默认配置
    
    Returns:
        MCP Servers 配置对象
    """
    # 1. 如果指定了配置文件路径
    if config_path and config_path.exists():
        logger.info(
            "mcp_config_loading",
            config_path=str(config_path),
        )
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)
            
            config = MCPServersConfig(**config_data)
            
            logger.info(
                "mcp_config_loaded",
                config_path=str(config_path),
                servers_count=len(config.servers),
                enabled_count=len(config.get_enabled_servers()),
            )
            
            return config
        
        except Exception as e:
            logger.error(
                "mcp_config_load_failed",
                config_path=str(config_path),
                error=str(e),
            )
            logger.warning("使用默认 MCP 配置")
            return DEFAULT_MCP_SERVERS
    
    # 2. 尝试从默认路径加载
    default_paths = [
        Path("./mcp_servers.json"),
        Path("backend/mcp_servers.json"),
        Path("../mcp_servers.json"),
    ]
    
    for path in default_paths:
        if path.exists():
            logger.info(
                "mcp_config_found",
                config_path=str(path),
            )
            return load_mcp_config(path)
    
    # 3. 使用默认配置
    logger.info(
        "mcp_config_using_default",
        message="未找到 mcp_servers.json，使用默认配置（无 MCP Server）"
    )
    return DEFAULT_MCP_SERVERS


def save_mcp_config(
    config: MCPServersConfig,
    config_path: Path = Path("backend/mcp_servers.json")
):
    """
    保存 MCP Server 配置到文件
    
    Args:
        config: MCP Servers 配置对象
        config_path: 配置文件路径
    """
    try:
        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存配置
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(
                config.model_dump(),
                f,
                indent=2,
                ensure_ascii=False,
            )
        
        logger.info(
            "mcp_config_saved",
            config_path=str(config_path),
            servers_count=len(config.servers),
        )
    
    except Exception as e:
        logger.error(
            "mcp_config_save_failed",
            config_path=str(config_path),
            error=str(e),
        )
        raise


# ============================================================
# 配置示例生成
# ============================================================

def generate_example_config(output_path: Path = Path("backend/mcp_servers.example.json")):
    """
    生成示例配置文件
    
    Args:
        output_path: 输出文件路径
    """
    example_config = MCPServersConfig(
        servers=[
            MCPServerConfig(
                name="filesystem",
                description="File system operations (read, write, list files)",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-filesystem"],
                enabled=False,
            ),
            MCPServerConfig(
                name="github",
                description="GitHub API integration",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                enabled=False,
            ),
            MCPServerConfig(
                name="postgres",
                description="PostgreSQL database integration",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-postgres"],
                enabled=False,
                env={
                    "POSTGRES_CONNECTION_STRING": "postgresql://user:password@localhost:5432/dbname"
                },
            ),
        ]
    )
    
    save_mcp_config(example_config, output_path)
    
    logger.info(
        "mcp_example_config_generated",
        output_path=str(output_path),
        message="示例配置文件已生成",
    )


if __name__ == "__main__":
    # 生成示例配置文件
    generate_example_config()

