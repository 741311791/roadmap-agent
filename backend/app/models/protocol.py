"""
通信协议模型（ACSMessage）
"""
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Literal
import uuid
import time


class ACSMessage(BaseModel):
    """Agent Communication Standard (ACS) 信封"""
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    sender: str = Field(..., description="发送方 Agent ID")
    receiver: str = Field(..., description="接收方 Agent ID 或 'orchestrator'")
    type: Literal["COMMAND", "RESPONSE", "EVENT", "ERROR"]

    # 核心载荷：存放 Interface Model 的字典
    content: Dict[str, Any]

    # 状态引用：指向 GlobalState 中的大对象
    context_ref: Optional[str] = None

    # 元数据
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="附加信息：token 消耗、延迟等"
    )

