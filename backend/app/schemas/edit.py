"""
编辑记录 Schema 定义

用于路线图编辑历史记录的数据传输对象。
"""
from typing import Optional
from pydantic import BaseModel, Field


class EditRecordResponse(BaseModel):
    """
    编辑记录响应
    
    单条编辑记录的完整信息。
    """
    id: str = Field(..., description="编辑记录ID")
    task_id: str = Field(..., description="任务ID")
    version: int = Field(..., description="版本号")
    edit_type: str = Field(..., description="编辑类型（human_review/validation_failed）")
    human_feedback: Optional[str] = Field(None, description="人工反馈内容")
    modifications_count: int = Field(..., description="修改数量")
    created_at: str = Field(..., description="创建时间（ISO格式）")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "edit-123",
                    "task_id": "task-456",
                    "version": 2,
                    "edit_type": "human_review",
                    "human_feedback": "需要调整学习路径顺序",
                    "modifications_count": 3,
                    "created_at": "2026-01-07T10:00:00Z"
                }
            ]
        }
    }


class EditRecordListResponse(BaseModel):
    """
    编辑记录列表响应
    
    包含多条编辑记录和总数统计。
    """
    records: list[EditRecordResponse] = Field(..., description="编辑记录列表")
    total: int = Field(..., description="总记录数")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "records": [
                        {
                            "id": "edit-123",
                            "task_id": "task-456",
                            "version": 2,
                            "edit_type": "human_review",
                            "human_feedback": "需要调整学习路径顺序",
                            "modifications_count": 3,
                            "created_at": "2026-01-07T10:00:00Z"
                        }
                    ],
                    "total": 5
                }
            ]
        }
    }


class RoadmapComparisonResponse(BaseModel):
    """
    路线图对比响应
    
    用于展示路线图不同版本之间的差异。
    """
    task_id: str = Field(..., description="任务ID")
    current_version: int = Field(..., description="当前版本号")
    previous_version: int = Field(..., description="前一版本号")
    comparison: dict = Field(..., description="对比详情（结构化差异数据）")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "task_id": "task-456",
                    "current_version": 3,
                    "previous_version": 2,
                    "comparison": {
                        "added_concepts": ["新概念1"],
                        "removed_concepts": [],
                        "modified_concepts": ["修改的概念1"]
                    }
                }
            ]
        }
    }

