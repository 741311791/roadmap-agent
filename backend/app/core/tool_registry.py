"""
工具注册中心

按时序图，工具层包含：
- Web Search: 搜索资料
- S3 Object Storage: 存储教程内容
"""
from typing import Dict, Optional
from app.tools.base import BaseTool
from app.tools.search.web_search import WebSearchTool
from app.tools.storage.s3_client import S3StorageTool
import structlog

logger = structlog.get_logger()


class ToolRegistry:
    """工具注册中心（单例模式）"""
    
    _instance: Optional["ToolRegistry"] = None
    _tools: Dict[str, BaseTool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化工具注册表"""
        # 注册 Web Search Tool
        self.register(WebSearchTool())
        # 注册 S3 Storage Tool
        self.register(S3StorageTool())
        logger.info("tool_registry_initialized", tools_count=len(self._tools))
    
    def register(self, tool: BaseTool):
        """
        注册工具
        
        Args:
            tool: 工具实例
        """
        self._tools[tool.tool_id] = tool
        logger.info("tool_registered", tool_id=tool.tool_id)
    
    def get(self, tool_id: str) -> Optional[BaseTool]:
        """
        获取工具
        
        Args:
            tool_id: 工具 ID
            
        Returns:
            工具实例，如果不存在则返回 None
        """
        return self._tools.get(tool_id)
    
    def list_all(self) -> Dict[str, BaseTool]:
        """获取所有已注册的工具"""
        return self._tools.copy()


# 全局单例
tool_registry = ToolRegistry()
