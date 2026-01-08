"""
执行日志追踪 Schema 定义

用于路线图生成过程的执行日志数据传输对象。
"""
from typing import Optional
from pydantic import BaseModel, Field


class ExecutionLogResponse(BaseModel):
    """
    执行日志响应
    
    单条执行日志的完整信息。
    """
    id: str = Field(..., description="日志ID")
    task_id: str = Field(..., description="任务ID")
    roadmap_id: Optional[str] = Field(None, description="路线图ID")
    concept_id: Optional[str] = Field(None, description="概念ID")
    level: str = Field(..., description="日志级别（info/warning/error）")
    category: str = Field(..., description="日志分类（agent/system/validation等）")
    step: Optional[str] = Field(None, description="执行步骤")
    agent_name: Optional[str] = Field(None, description="Agent名称")
    message: str = Field(..., description="日志消息")
    details: Optional[dict] = Field(None, description="详细信息（JSON格式）")
    duration_ms: Optional[int] = Field(None, description="耗时（毫秒）")
    created_at: str = Field(..., description="创建时间（ISO格式）")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "log-123",
                    "task_id": "task-456",
                    "roadmap_id": "roadmap-789",
                    "concept_id": None,
                    "level": "info",
                    "category": "agent",
                    "step": "intent_analysis",
                    "agent_name": "IntentAnalyzer",
                    "message": "意图分析完成",
                    "details": {"keywords": ["Python", "Web"]},
                    "duration_ms": 1250,
                    "created_at": "2026-01-07T09:00:00Z"
                }
            ]
        }
    }


class ExecutionLogListResponse(BaseModel):
    """
    执行日志列表响应
    
    包含多条日志和分页信息。
    """
    logs: list[ExecutionLogResponse] = Field(..., description="日志列表")
    total: int = Field(..., description="总日志数")
    offset: int = Field(..., description="分页偏移")
    limit: int = Field(..., description="每页数量")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "logs": [],
                    "total": 150,
                    "offset": 0,
                    "limit": 100
                }
            ]
        }
    }


class TraceSummaryResponse(BaseModel):
    """
    追踪摘要响应
    
    任务的日志统计信息。
    """
    task_id: str = Field(..., description="任务ID")
    level_stats: dict[str, int] = Field(..., description="按日志级别统计")
    category_stats: dict[str, int] = Field(..., description="按分类统计")
    total_duration_ms: int = Field(..., description="总耗时（毫秒）")
    first_log_at: Optional[str] = Field(None, description="首条日志时间")
    last_log_at: Optional[str] = Field(None, description="末条日志时间")
    total_logs: int = Field(..., description="总日志数")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task_id": "task-456",
                    "level_stats": {"info": 100, "warning": 10, "error": 2},
                    "category_stats": {"agent": 80, "system": 20, "validation": 12},
                    "total_duration_ms": 45000,
                    "first_log_at": "2026-01-07T09:00:00Z",
                    "last_log_at": "2026-01-07T09:00:45Z",
                    "total_logs": 112
                }
            ]
        }
    }

