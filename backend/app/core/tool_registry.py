"""
工具注册中心

按时序图，工具层包含：
- Web Search: 搜索资料
- S3 Object Storage: 存储教程内容
- Mentor Tools: 伴学Agent专用工具
"""
from typing import Dict, Optional
from app.tools.base import BaseTool
from app.tools.search.web_search_router import WebSearchRouter
from app.tools.search.duckduckgo_search import DuckDuckGoSearchTool
from app.tools.storage.s3_client import S3StorageTool
# 伴学Agent工具
from app.tools.mentor.note_recorder_tool import NoteRecorderTool
from app.tools.mentor.get_concept_tutorial_tool import GetConceptTutorialTool
from app.tools.mentor.get_user_profile_tool import GetUserProfileTool
from app.tools.mentor.get_roadmap_metadata_tool import GetRoadmapMetadataTool
from app.tools.mentor.mark_content_complete_tool import MarkContentCompleteTool
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
        """
        初始化工具注册表
        
        工具架构（简化后）：
        - WebSearchRouter (web_search_v1): 主要搜索工具，按优先级路由（Tavily → DuckDuckGo）
        - DuckDuckGoSearchTool (duckduckgo_search): DuckDuckGo 专用工具
        - S3StorageTool: 对象存储工具
        
        注意：TavilyAPISearchTool 需要数据库会话，因此由 WebSearchRouter 动态创建，不在此注册。
        """
        # 注册 Web Search Router（统一的搜索入口）
        # 按优先级：Tavily API（从数据库读取配额）→ DuckDuckGo
        try:
            self.register(WebSearchRouter())
        except Exception as e:
            logger.error(
                "web_search_router_registration_failed",
                error=str(e),
                message="Web Search Router 注册失败"
            )
        
        # 注册 DuckDuckGo 工具（可被其他组件直接使用）
        try:
            self.register(DuckDuckGoSearchTool())
        except Exception as e:
            logger.warning(
                "duckduckgo_tool_registration_failed",
                error=str(e),
                message="DuckDuckGo 工具注册失败"
            )
        
        # 注册 S3 Storage Tool
        self.register(S3StorageTool())
        
        # 注册伴学Agent工具
        try:
            self.register(NoteRecorderTool())
            self.register(GetConceptTutorialTool())
            self.register(GetUserProfileTool())
            self.register(GetRoadmapMetadataTool())
            self.register(MarkContentCompleteTool())
        except Exception as e:
            logger.error(
                "mentor_tools_registration_failed",
                error=str(e),
                message="伴学Agent工具注册失败"
            )
        
        logger.info(
            "tool_registry_initialized",
            tools_count=len(self._tools),
            tools=list(self._tools.keys())
        )
    
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
