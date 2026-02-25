"""
LangChain 工具包装器

使用 @tool 装饰器将项目现有的 BaseTool 转换为 LangChain 标准工具

注意：
- web_search 工具已移除（2026-01-18）
  原因：需要配合网页内容提取功能，暂不开发
  
- TutorialGeneratorAgent 现在采用场景区分策略：
  - 开发场景：使用 Context7 MCP 工具查询官方文档
  - 非开发场景：直接使用 LLM 知识库
  
此文件保留作为未来自定义工具的模板
"""
from langchain.tools import tool
import structlog

logger = structlog.get_logger()


async def get_langchain_tools() -> list:
    """
    获取所有 LangChain 兼容的工具
    
    Returns:
        工具列表（目前为空，保留作为未来扩展接口）
    """
    tools = []
    
    # 未来可以在这里添加新的自定义工具
    # 示例：
    # tools.append(my_custom_tool)
    
    logger.info(
        "langchain_tools_loaded",
        tools_count=len(tools),
        note="No custom tools currently (web_search removed)"
    )
    
    return tools

