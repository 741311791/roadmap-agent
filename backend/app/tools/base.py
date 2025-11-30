"""
Tool 基类
"""
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseTool(ABC, Generic[InputT, OutputT]):
    """工具抽象基类"""
    
    def __init__(self, tool_id: str):
        self.tool_id = tool_id
    
    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        """
        执行工具（由子类实现）
        
        Args:
            input_data: 工具输入
            
        Returns:
            工具输出
        """
        pass

