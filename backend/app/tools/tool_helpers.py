"""
工具辅助函数

提供工具调用的常用辅助方法，简化 Agent 中的代码。
"""
from typing import Dict, Any, Optional
from app.tools.registry import ToolRegistry
import structlog

logger = structlog.get_logger()


# ============================================================
# 全局 ToolRegistry 单例（向后兼容）
# ============================================================

_global_tool_registry: Optional[ToolRegistry] = None


def get_global_tool_registry() -> ToolRegistry:
    """
    获取全局 ToolRegistry 单例
    
    用于向后兼容旧代码中的 tool_registry.get() 调用
    
    Returns:
        ToolRegistry 实例
    """
    global _global_tool_registry
    
    if _global_tool_registry is None:
        _global_tool_registry = ToolRegistry()
        
        # 注册默认工具
        from app.tools.search.web_search_router import WebSearchRouter
        from app.tools.storage.s3_client import S3StorageTool
        from app.tools.mentor.get_concept_tutorial_tool import GetConceptTutorialTool
        from app.tools.mentor.get_user_profile_tool import GetUserProfileTool
        from app.tools.mentor.get_roadmap_metadata_tool import GetRoadmapMetadataTool
        # from app.tools.mentor.note_recorder_tool import NoteRecorderTool  # 已移除
        from app.tools.mentor.mark_content_complete_tool import MarkContentCompleteTool
        
        _global_tool_registry.register(WebSearchRouter())
        _global_tool_registry.register(S3StorageTool())
        _global_tool_registry.register(GetConceptTutorialTool())
        _global_tool_registry.register(GetUserProfileTool())
        _global_tool_registry.register(GetRoadmapMetadataTool())
        # _global_tool_registry.register(NoteRecorderTool())  # 已移除
        _global_tool_registry.register(MarkContentCompleteTool())
        
        logger.info(
            "global_tool_registry_initialized",
            tools_count=len(_global_tool_registry.list_tools()),
        )
    
    return _global_tool_registry


# ============================================================
# 兼容层：模拟旧的 tool_registry 接口
# ============================================================

class LegacyToolRegistryAdapter:
    """
    旧 tool_registry 接口适配器
    
    用于向后兼容，将旧的 tool_id 调用映射到新的 name 调用
    """
    
    def __init__(self):
        self._registry = get_global_tool_registry()
    
    def get(self, tool_id: str):
        """
        获取工具（兼容旧接口）
        
        版本号映射：
        - web_search_v1 → web_search
        - web_search_v2 → web_search
        - s3_storage_v1 → s3_upload
        - s3_storage_v2 → s3_upload
        """
        # 映射表：tool_id → tool_name
        id_to_name_mapping = {
            "web_search_v1": "web_search",
            "web_search_v2": "web_search",
            "duckduckgo_search": "duckduckgo_search",
            "s3_storage_v1": "s3_upload",
            "s3_storage_v2": "s3_upload",
            "get_concept_tutorial_v1": "get_concept_tutorial",
            "get_concept_tutorial_v2": "get_concept_tutorial",
            "get_user_profile_v1": "get_user_profile",
            "get_user_profile_v2": "get_user_profile",
            "get_roadmap_metadata_v1": "get_roadmap_metadata",
            "get_roadmap_metadata_v2": "get_roadmap_metadata",
            "note_recorder_v1": "record_note",
            "note_recorder_v2": "record_note",
            "mark_content_complete_v1": "mark_content_complete",
            "mark_content_complete_v2": "mark_content_complete",
        }
        
        # 尝试映射
        tool_name = id_to_name_mapping.get(tool_id, tool_id)
        tool = self._registry.get_tool(tool_name)
        
        if tool:
            logger.debug(
                "legacy_tool_registry_adapter",
                requested_id=tool_id,
                resolved_name=tool_name,
            )
        
        return tool
    
    def list_all(self) -> Dict[str, Any]:
        """列出所有工具（兼容旧接口）"""
        return {
            tool.tool_id: tool
            for tool in self._registry._tools.values()
        }


# 创建全局兼容实例
tool_registry = LegacyToolRegistryAdapter()

