"""
任务恢复相关Schemas
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import List


class TaskRecoveryReport(BaseModel):
    """任务恢复报告"""
    total_found: int = Field(..., description="找到的中断任务数")
    recovered: int = Field(..., description="成功恢复的任务数")
    failed: int = Field(..., description="恢复失败的任务数")
    no_checkpoint: int = Field(..., description="没有 checkpoint 的任务数")
    task_ids: List[str] = Field(..., description="尝试恢复的任务 ID 列表")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_found": 5,
                "recovered": 3,
                "failed": 1,
                "no_checkpoint": 1,
                "task_ids": [
                    "task-123-abc",
                    "task-456-def",
                    "task-789-ghi"
                ]
            }
        }
    )

