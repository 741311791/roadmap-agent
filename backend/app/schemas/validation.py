"""
验证记录 Schema 定义

用于路线图验证历史记录的数据传输对象。
"""
from typing import Optional
from pydantic import BaseModel, Field


class ValidationRecordResponse(BaseModel):
    """
    验证记录响应
    
    单条验证记录的完整信息。
    """
    id: str = Field(..., description="验证记录ID")
    task_id: str = Field(..., description="任务ID")
    version: int = Field(..., description="版本号")
    validation_status: str = Field(..., description="验证状态（passed/failed）")
    issues_found: int = Field(..., description="发现的问题数量")
    issues_details: Optional[list] = Field(None, description="问题详情列表")
    suggestions: Optional[list] = Field(None, description="优化建议列表")
    created_at: str = Field(..., description="创建时间（ISO格式）")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "validation-123",
                    "task_id": "task-456",
                    "version": 1,
                    "validation_status": "failed",
                    "issues_found": 2,
                    "issues_details": [
                        {"type": "循环依赖", "description": "概念A和B存在循环依赖"}
                    ],
                    "suggestions": [
                        "建议调整概念A的前置依赖"
                    ],
                    "created_at": "2026-01-07T09:30:00Z"
                }
            ]
        }
    }


class ValidationRecordListResponse(BaseModel):
    """
    验证记录列表响应
    
    包含多条验证记录和总数统计。
    """
    records: list[ValidationRecordResponse] = Field(..., description="验证记录列表")
    total: int = Field(..., description="总记录数")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "records": [
                        {
                            "id": "validation-123",
                            "task_id": "task-456",
                            "version": 1,
                            "validation_status": "failed",
                            "issues_found": 2,
                            "issues_details": [],
                            "suggestions": [],
                            "created_at": "2026-01-07T09:30:00Z"
                        }
                    ],
                    "total": 3
                }
            ]
        }
    }

