"""
Tool 基类（支持 RESTful 和 MCP 协议适配）

设计理念：
- 统一抽象层：无论底层是 HTTP 请求还是 MCP 协议，对 Agent 来说都是统一的接口
- Schema 标准化：使用 Pydantic 作为中间层，自动生成 LLM Function Schema
- 协议无关：为未来接入 MCP (Model Context Protocol) 预留扩展点
"""
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic, Dict, Type
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseTool(ABC, Generic[InputT, OutputT]):
    """
    统一工具基类
    
    支持两种协议适配：
    - RESTful API 工具（现有）
    - MCP 工具（未来扩展）
    
    设计特性：
    - 自动生成 LLM Function Schema（OpenAI/MCP 格式）
    - 统一的执行接口（异步）
    - 强类型约束（Pydantic Schema）
    - 结构化日志
    """
    
    def __init__(
        self, 
        tool_id: str,
        name: str,
        description: str,
        args_schema: Type[InputT],
    ):
        """
        初始化工具
        
        Args:
            tool_id: 工具唯一标识符（内部使用）
            name: 工具名称（LLM 调用时使用）
            description: 工具功能描述（LLM 可见）
            args_schema: 参数 Schema（Pydantic 模型）
        """
        self.tool_id = tool_id
        self.name = name
        self.description = description
        self.args_schema = args_schema
    
    @abstractmethod
    async def execute(self, input_data: InputT, **kwargs) -> OutputT:
        """
        执行工具（由子类实现）
        
        Args:
            input_data: 工具输入（已验证的 Pydantic 模型）
            **kwargs: 额外参数（如 db_session, pre_allocated_key 等）
            
        Returns:
            工具输出（Pydantic 模型）
        """
        pass
    
    def to_openai_function_schema(self) -> Dict:
        """
        转换为 OpenAI Function Calling 格式
        
        这样 Agent 就不需要手动定义工具 Schema 了
        
        Returns:
            OpenAI Function 格式的 Schema
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.args_schema.model_json_schema(),
            }
        }
    
    def to_mcp_tool_schema(self) -> Dict:
        """
        转换为 MCP Tool 格式（未来扩展）
        
        MCP (Model Context Protocol) 是新一代的 AI 工具标准协议
        
        Returns:
            MCP Tool 格式的 Schema
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.args_schema.model_json_schema(),
        }

