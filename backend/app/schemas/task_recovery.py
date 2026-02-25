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


class PendingTaskRecoveryReport(BaseModel):
    """Pending 任务重新入队报告"""
    total_found: int = Field(default=0, description="找到的孤儿 pending 任务数")
    re_enqueued: int = Field(default=0, description="成功重新入队的任务数")
    skipped: int = Field(default=0, description="因数据格式异常跳过的任务数")
    failed: int = Field(default=0, description="重新入队失败的任务数")
    task_ids: List[str] = Field(default_factory=list, description="尝试重新入队的任务 ID 列表")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_found": 2,
                "re_enqueued": 2,
                "skipped": 0,
                "failed": 0,
                "task_ids": [
                    "task-123-abc",
                    "task-456-def"
                ]
            }
        }
    )

