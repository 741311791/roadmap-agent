"""
路线图重试相关 Schema

基于LangGraph 1.0 Checkpoint机制的两种重试模式：

1. **断点续传（Resume from Checkpoint）**：
   - 从最后的checkpoint恢复（主图或子图）
   - 适用于任意节点失败后重新启动
   - 参考：https://docs.langchain.com/oss/python/langgraph/persistence

2. **时间旅行（Time Travel）**：
   - 回到主图历史节点重新执行
   - 仅支持主图节点，不支持子图节点
   - 参考：https://docs.langchain.com/oss/python/langgraph/use-time-travel

注意：概念内容重新生成属于Concept编辑服务，不属于Retry功能
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from enum import Enum


class RetryMode(str, Enum):
    """
    重试模式枚举
    
    明确区分两种重试机制，避免混淆
    """
    RESUME = "resume"  # 断点续传：从最后checkpoint恢复
    TIME_TRAVEL = "time_travel"  # 时间旅行：回到历史节点


class MainGraphNode(str, Enum):
    """
    主图节点枚举
    
    用于时间旅行，指定回到哪个主图节点
    注意：子图节点暂不支持时间旅行
    """
    INTENT = "intent_analysis"
    CURRICULUM = "curriculum_design"
    VALIDATION = "structure_validation"
    REVIEW = "human_review"
    CONTENT = "content_generation"
    # 注意：Edit相关节点（edit_plan_analysis, roadmap_edit）也可以添加


class RetryScope(str, Enum):
    """
    重试范围枚举
    
    表示重试操作影响的范围
    """
    TASK = "task"  # 从最后的checkpoint恢复（默认）
    STAGE = "stage"  # 从特定阶段重新开始
    CONCEPT = "concept"  # 重试单个Concept的内容


class RetryRequest(BaseModel):
    """
    统一的重试请求Schema
    
    支持两种模式：
    1. mode=resume：断点续传（从最后checkpoint恢复）
    2. mode=time_travel + target_node：时间旅行（回到指定主图节点）
    """
    mode: RetryMode = Field(
        default=RetryMode.RESUME,
        description="重试模式：resume（断点续传）或 time_travel（时间旅行）"
    )
    
    # 时间旅行参数
    target_node: Optional[MainGraphNode] = Field(
        default=None,
        description="目标主图节点（仅当mode=time_travel时有效）"
    )
    
    # 通用参数
    reason: Optional[str] = Field(
        default=None,
        description="重试原因（用于日志记录和审计）"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "mode": "resume",
                    "reason": "Worker重启后从失败点恢复"
                },
                {
                    "mode": "time_travel",
                    "target_node": "intent_analysis",
                    "reason": "用户需求变更，从Intent阶段重新开始"
                }
            ]
        }
    )


class RetryResponse(BaseModel):
    """重试响应Schema"""
    success: bool = Field(description="重试是否成功启动")
    message: str = Field(description="响应消息")
    task_id: str = Field(description="任务ID")
    celery_task_id: Optional[str] = Field(
        default=None,
        description="新的Celery任务ID（如果创建了新任务）"
    )
    retry_scope: RetryScope = Field(description="实际执行的重试范围")
    retry_from: Optional[str] = Field(
        default=None,
        description="从哪个节点/阶段开始重试"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "路线图生成任务已从checkpoint恢复",
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "celery_task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "retry_scope": "task",
                "retry_from": "content_generation"
            }
        }
    )


class CheckpointInfo(BaseModel):
    """Checkpoint信息Schema（用于调试和前端展示）"""
    checkpoint_id: str = Field(description="Checkpoint ID")
    timestamp: str = Field(description="创建时间")
    node_name: str = Field(description="执行的节点名称")
    next_nodes: List[str] = Field(description="下一步要执行的节点列表")
    can_retry: bool = Field(description="是否可以从此checkpoint重试")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "checkpoint_id": "1ef12345-6789-4abc-def0-123456789abc",
                "timestamp": "2026-01-11T10:30:00Z",
                "node_name": "content_generation",
                "next_nodes": [],
                "can_retry": True
            }
        }
    )


class TaskRetryStatus(BaseModel):
    """
    任务重试状态Schema
    
    提供任务当前状态和可用的重试模式信息
    """
    task_id: str
    can_retry: bool = Field(description="当前是否可以重试")
    retry_reason: Optional[str] = Field(
        default=None,
        description="如果不能重试，说明原因"
    )
    current_checkpoint: Optional[CheckpointInfo] = Field(
        default=None,
        description="当前主图的checkpoint信息"
    )
    is_subgraph_interrupted: bool = Field(
        default=False,
        description="是否有子图在中断状态（需要特殊处理）"
    )
    available_modes: List[RetryMode] = Field(
        description="可用的重试模式"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "task_id": "550e8400-e29b-41d4-a716-446655440000",
                    "can_retry": True,
                    "retry_reason": None,
                    "current_checkpoint": {
                        "checkpoint_id": "1ef12345-6789-4abc-def0-123456789abc",
                        "timestamp": "2026-01-11T10:30:00Z",
                        "node_name": "content_generation",
                        "next_nodes": [],
                        "can_retry": True
                    },
                    "is_subgraph_interrupted": True,
                    "available_modes": ["resume", "time_travel"]
                }
            ]
        }
    )

