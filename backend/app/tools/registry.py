"""
工具注册中心（Tool Registry）

职责：
- 管理所有可用工具的生命周期
- 自动生成 LLM Function Schema
- 提供统一的工具调用接口
- 支持 MCP 服务连接管理（未来扩展）

设计模式：
- 注册中心模式 (Registry Pattern)
- 适配器模式 (Adapter Pattern)
- 工厂模式 (Factory Pattern)
"""
from typing import Dict, List, Any, Optional, Literal
from app.tools.base import BaseTool
import structlog
import json

logger = structlog.get_logger()


class ToolRegistry:
    """
    工具注册中心
    
    核心功能：
    1. 工具注册与管理
    2. Schema 自动生成（OpenAI/MCP 格式）
    3. 统一的工具执行接口
    4. 错误处理（返回错误描述而非抛出异常，让 LLM 自我修正）
    5. 生命周期管理（MCP 连接）
    
    使用示例：
    ```python
    # 初始化
    registry = ToolRegistry()
    
    # 注册工具
    registry.register(WebSearchTool())
    registry.register(GetConceptTutorialTool())
    
    # 在 Agent 中使用
    tools_schema = registry.get_all_schemas(format="openai")
    response = await agent._call_llm(messages, tools=tools_schema)
    
    # 执行工具
    result = await registry.execute_tool(
        name="web_search",
        arguments={"query": "Python tutorial"},
    )
    ```
    """
    
    def __init__(self):
        """初始化工具注册中心"""
        self._tools: Dict[str, BaseTool] = {}
        self._mcp_sessions: List[Any] = []  # 未来用于管理 MCP 连接
    
    def register(self, tool: BaseTool):
        """
        注册工具
        
        Args:
            tool: 工具实例（必须继承 BaseTool）
            
        注意：
        - 如果工具名称已存在，将覆盖旧工具
        - 注册时会记录日志
        """
        if tool.name in self._tools:
            logger.warning(
                "tool_already_registered",
                tool_name=tool.name,
                old_tool_id=self._tools[tool.name].tool_id,
                new_tool_id=tool.tool_id,
                message="工具已存在，将被覆盖"
            )
        
        self._tools[tool.name] = tool
        
        logger.info(
            "tool_registered",
            tool_name=tool.name,
            tool_id=tool.tool_id,
            total_tools=len(self._tools),
        )
    
    def unregister(self, tool_name: str) -> bool:
        """
        取消注册工具
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否成功取消注册
        """
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(
                "tool_unregistered",
                tool_name=tool_name,
                total_tools=len(self._tools),
            )
            return True
        return False
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        获取工具实例
        
        Args:
            name: 工具名称
            
        Returns:
            工具实例，如果不存在则返回 None
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """
        列出所有已注册的工具名称
        
        Returns:
            工具名称列表
        """
        return list(self._tools.keys())
    
    def get_all_schemas(
        self, 
        format: Literal["openai", "mcp"] = "openai"
    ) -> List[Dict]:
        """
        获取所有工具的 Schema（用于 LLM Function Calling）
        
        Args:
            format: Schema 格式
                - "openai": OpenAI Function Calling 格式（默认）
                - "mcp": MCP Tool 格式（未来扩展）
            
        Returns:
            工具 Schema 列表
            
        Raises:
            ValueError: 如果 format 不支持
        """
        if format == "openai":
            return [
                tool.to_openai_function_schema() 
                for tool in self._tools.values()
            ]
        elif format == "mcp":
            return [
                tool.to_mcp_tool_schema() 
                for tool in self._tools.values()
            ]
        else:
            raise ValueError(
                f"不支持的 Schema 格式: {format}。"
                f"支持的格式: 'openai', 'mcp'"
            )
    
    async def execute_tool(
        self, 
        name: str, 
        arguments: Dict,
        **kwargs
    ) -> Any:
        """
        统一的工具执行接口
        
        设计原则：
        - 不抛出异常，返回错误描述字符串
        - 让 LLM 看到错误信息并自我修正（Self-Refine）
        - 统一的日志记录
        
        Args:
            name: 工具名称（来自 LLM 的 tool_call）
            arguments: 工具参数（JSON 字典）
            **kwargs: 额外参数（如 db_session, pre_allocated_tavily_key）
            
        Returns:
            工具执行结果（成功时返回结果，失败时返回错误描述字符串）
            
        使用示例：
        ```python
        # Agent 中处理 tool_calls
        for tool_call in message.tool_calls:
            result = await registry.execute_tool(
                name=tool_call.function.name,
                arguments=json.loads(tool_call.function.arguments),
                pre_allocated_tavily_key=self.tavily_key,
            )
            
            # result 可能是成功结果，也可能是 "Error: ..." 字符串
            # LLM 会根据结果调整后续行为
        ```
        """
        # 1. 检查工具是否存在
        tool = self.get_tool(name)
        if not tool:
            error_msg = f"工具 '{name}' 未注册"
            logger.error(
                "tool_not_found",
                tool_name=name,
                available_tools=self.list_tools(),
            )
            # 返回错误字符串（而非抛出异常）
            return f"Error: {error_msg}. Available tools: {', '.join(self.list_tools())}"
        
        # 2. 执行工具（捕获所有异常）
        try:
            # 2.1 验证并解析参数
            input_data = tool.args_schema(**arguments)
            
            logger.info(
                "tool_execution_start",
                tool_name=name,
                tool_id=tool.tool_id,
                arguments=arguments,
            )
            
            # 2.2 执行工具
            result = await tool.execute(input_data, **kwargs)
            
            logger.info(
                "tool_execution_success",
                tool_name=name,
                tool_id=tool.tool_id,
            )
            
            return result
        
        except Exception as e:
            # 捕获所有异常（参数验证失败、网络错误、业务逻辑错误等）
            logger.error(
                "tool_execution_failed",
                tool_name=name,
                tool_id=tool.tool_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            
            # 返回错误描述（让 LLM 看到并可能重试或调整策略）
            return f"Error executing '{name}': {str(e)}"
    
    # ============================================================
    # MCP相关方法已废弃 (2026-01-19)
    # 原因：统一使用官方 langchain-mcp-adapters
    # 现在Agent直接使用 app/tools/mcp_loader.py 加载MCP工具
    # ============================================================
    
    # async def load_mcp_server(...): 已删除
    # async def cleanup(...): 已删除
    # 
    # 如需使用MCP工具，请参考：
    # - app/tools/mcp_loader.py - 官方langchain-mcp-adapters加载器
    # - app/agents/tutorial_generator.py - 使用示例
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"ToolRegistry(tools={len(self._tools)}, mcp_sessions={len(self._mcp_sessions)})"


# ============================================================
# 全局单例实例（可选）
# ============================================================
# 如果希望在整个应用中共享同一个 Registry，可以使用全局实例
# 但建议通过依赖注入的方式传递（如在 AgentFactory 中创建）
# _global_registry: Optional[ToolRegistry] = None


# def get_global_registry() -> ToolRegistry:
#     """获取全局工具注册中心（单例模式）"""
#     global _global_registry
#     if _global_registry is None:
#         _global_registry = ToolRegistry()
#     return _global_registry

