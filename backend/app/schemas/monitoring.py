"""
Celery 任务队列监控 Schema

用于 Celery 任务状态查询和 Worker 监控的请求/响应模型。
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================
# Celery 任务相关
# ============================================================

class CeleryTaskInfo(BaseModel):
    """
    Celery 任务信息
    
    Args:
        task_id: 任务 ID
        task_name: 任务名称
        queue: 队列名称
        status: 任务状态 (PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED)
        worker: Worker 名称
        started_at: 开始时间
        completed_at: 完成时间
        duration: 执行耗时（秒）
        args: 任务参数
        kwargs: 任务关键字参数
        result: 任务结果
        error: 错误信息
    """
    task_id: str = Field(..., description="任务 ID")
    task_name: str = Field(..., description="任务名称")
    queue: Optional[str] = Field(None, description="队列名称")
    status: str = Field(..., description="任务状态")
    worker: Optional[str] = Field(None, description="Worker 名称")
    started_at: Optional[str] = Field(None, description="开始时间 (ISO 格式)")
    completed_at: Optional[str] = Field(None, description="完成时间 (ISO 格式)")
    duration: Optional[float] = Field(None, description="执行耗时（秒）")
    args: Optional[List[Any]] = Field(None, description="任务参数")
    kwargs: Optional[Dict[str, Any]] = Field(None, description="任务关键字参数")
    result: Optional[Any] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="错误信息")


class CeleryOverview(BaseModel):
    """
    Celery 任务队列总览
    
    Args:
        active_count: 活跃任务数
        pending_count: 待处理任务数（预约+保留）
        scheduled_count: 预约任务数
        reserved_count: 保留任务数
        queue_lengths: 各队列长度统计
        workers: Worker 列表
    """
    active_count: int = Field(..., description="活跃任务数")
    pending_count: int = Field(..., description="待处理任务数")
    scheduled_count: int = Field(..., description="预约任务数")
    reserved_count: int = Field(..., description="保留任务数")
    queue_lengths: Dict[str, int] = Field(..., description="各队列长度统计")
    workers: List[str] = Field(..., description="Worker 列表")


class CeleryTaskListResponse(BaseModel):
    """
    Celery 任务列表响应
    
    Args:
        tasks: 任务列表
        total: 总数
    """
    tasks: List[CeleryTaskInfo] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")


# ============================================================
# Celery Worker 相关
# ============================================================

class CeleryWorkerInfo(BaseModel):
    """
    Celery Worker 信息
    
    Args:
        hostname: Worker 主机名
        status: Worker 状态
        active_tasks: 活跃任务数
        processed_tasks: 已处理任务数
    """
    hostname: str = Field(..., description="Worker 主机名")
    status: str = Field(..., description="Worker 状态")
    active_tasks: int = Field(..., description="活跃任务数")
    processed_tasks: Optional[int] = Field(None, description="已处理任务数")


class CeleryWorkerListResponse(BaseModel):
    """
    Celery Worker 列表响应
    
    Args:
        workers: Worker 列表
        total: 总数
    """
    workers: List[CeleryWorkerInfo] = Field(..., description="Worker 列表")
    total: int = Field(..., description="总数")

