"""
Celery 任务队列监控 Schema

用于 Celery 任务状态查询和 Worker 监控的请求/响应模型。

重构说明：
- 列表/详情接口改为 DB-first，主源是 RoadmapTask，runtime 信息作为补充
- 新增业务任务字段（workflow_status、current_step、roadmap_id 等）
- 新增 inspect_available 标记，避免超时时伪装成空数据
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ============================================================
# Celery 任务相关（重构为混合数据模型）
# ============================================================

class CeleryTaskInfo(BaseModel):
    """
    Celery/业务任务混合信息

    数据来源：
    - 主源：roadmap_tasks（DB 持久化）
    - 补充：Celery inspect / AsyncResult（runtime）

    Args:
        task_id: 业务任务 ID（roadmap_tasks.task_id）
        task_name: Celery 任务名称（runtime）或业务任务类型描述
        queue: 队列名称（runtime）
        status: Celery runtime 状态（STARTED/SCHEDULED/RESERVED 等）
        workflow_status: 业务工作流状态（pending/processing/completed/failed 等）
        current_step: 当前工作流步骤（来自 DB 或 live_step）
        task_type: 业务任务类型（creation/retry_tutorial 等）
        roadmap_id: 关联的路线图 ID
        celery_task_id: Celery 原生任务 ID
        content_generation_status: 内容生成子任务状态
        worker: Worker 名称（runtime）
        started_at: 开始时间
        completed_at: 完成时间
        duration: 执行耗时（秒）
        args: 任务参数（runtime）
        kwargs: 任务关键字参数（runtime）
        result: 任务结果
        error: 错误信息（Celery）
        error_message: 业务错误信息（DB）
        live_step: Redis 实时步骤（仍在执行时有值）
        source: 数据来源标记（runtime/database/hybrid）
    """
    # 核心标识
    task_id: str = Field(..., description="业务任务 ID")
    task_name: str = Field(..., description="任务名称或类型描述")

    # runtime 信息（Celery inspect）
    queue: Optional[str] = Field(None, description="队列名称")
    status: str = Field(..., description="Celery/汇总状态")
    worker: Optional[str] = Field(None, description="Worker 名称")
    started_at: Optional[str] = Field(None, description="开始时间 (ISO 格式)")
    updated_at: Optional[str] = Field(None, description="最近更新时间 (ISO 格式)")
    completed_at: Optional[str] = Field(None, description="完成时间 (ISO 格式)")
    duration: Optional[float] = Field(None, description="执行耗时（秒）")
    args: Optional[List[Any]] = Field(None, description="任务参数")
    kwargs: Optional[Dict[str, Any]] = Field(None, description="任务关键字参数")
    result: Optional[Any] = Field(None, description="任务结果")
    error: Optional[str] = Field(None, description="Celery 错误信息")

    # 业务字段（DB）
    workflow_status: Optional[str] = Field(None, description="业务工作流状态")
    current_step: Optional[str] = Field(None, description="当前工作流步骤")
    task_type: Optional[str] = Field(None, description="业务任务类型")
    roadmap_id: Optional[str] = Field(None, description="关联的路线图 ID")
    celery_task_id: Optional[str] = Field(None, description="Celery 原生任务 ID")
    content_generation_status: Optional[str] = Field(None, description="内容生成状态")
    error_message: Optional[str] = Field(None, description="业务错误信息（DB）")
    live_step: Optional[str] = Field(None, description="Redis 实时步骤")
    is_stale: bool = Field(False, description="是否为长期未更新的卡住任务")
    stale_for_seconds: Optional[float] = Field(None, description="已卡住时长（秒）")
    has_runtime_presence: Optional[bool] = Field(None, description="Celery runtime 中是否仍可见")
    can_safe_cleanup: bool = Field(False, description="管理员是否可以执行安全清理")
    can_force_cleanup: bool = Field(False, description="管理员是否可以直接执行清理")

    # 元数据
    source: str = Field("database", description="数据来源: runtime/database/hybrid")


class CeleryOverview(BaseModel):
    """
    管理员监控总览

    数据来源：
    - runtime 统计：Celery inspect（当 inspect_available=True 时有值）
    - DB 统计：roadmap_tasks 聚合（始终有值）

    Args:
        inspect_available: inspect 是否可用（超时或无 worker 时为 False）
        runtime_active_count: 当前活跃 Celery 任务数（runtime）
        runtime_pending_count: 当前排队/预约任务数（runtime）
        scheduled_count: 预约任务数（runtime）
        reserved_count: 保留任务数（runtime）
        workers_online: 在线 Worker 数
        queue_lengths: 各队列长度统计（runtime）
        workers: Worker 主机名列表（runtime）
        db_processing_count: 数据库中 processing 状态任务数
        db_pending_count: 数据库中 pending 状态任务数
        db_completed_24h: 过去 24 小时完成任务数
        db_failed_24h: 过去 24 小时失败任务数
        db_total_active: DB 中活跃任务数（pending + processing）
    """
    # runtime 统计
    inspect_available: bool = Field(..., description="Celery inspect 是否可用")
    runtime_active_count: int = Field(0, description="当前活跃 Celery 任务数")
    runtime_pending_count: int = Field(0, description="当前排队/预约 Celery 任务数")
    scheduled_count: int = Field(0, description="预约任务数")
    reserved_count: int = Field(0, description="保留任务数")
    workers_online: int = Field(0, description="在线 Worker 数")
    queue_lengths: Dict[str, int] = Field(default_factory=dict, description="各队列长度统计")
    workers: List[str] = Field(default_factory=list, description="Worker 主机名列表")
    heartbeat_available: bool = Field(False, description="Worker heartbeat 是否可用")
    heartbeat_workers_online: int = Field(0, description="通过 heartbeat 检测到的在线 Worker 数")
    heartbeat_workers: List[str] = Field(default_factory=list, description="通过 heartbeat 检测到的 Worker 主机名列表")

    # DB 统计（始终有值）
    db_processing_count: int = Field(0, description="DB 中 processing 状态任务数")
    db_pending_count: int = Field(0, description="DB 中 pending 状态任务数")
    db_completed_24h: int = Field(0, description="过去 24 小时完成任务数")
    db_failed_24h: int = Field(0, description="过去 24 小时失败任务数")
    db_total_active: int = Field(0, description="DB 中活跃任务数（pending + processing）")
    stale_processing_count: int = Field(0, description="当前已达到卡住阈值的 processing 任务数")
    cleanable_stale_processing_count: int = Field(0, description="当前可安全清理的卡住任务数")
    force_cleanable_stale_processing_count: int = Field(0, description="当前可强制清理的卡住任务数")


class CeleryTaskListResponse(BaseModel):
    """
    监控任务列表响应

    Args:
        tasks: 任务列表（DB 历史 + runtime 补充）
        total: 总数
    """
    tasks: List[CeleryTaskInfo] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")


class CeleryTaskCleanupResponse(BaseModel):
    """
    单个卡住任务清理结果

    Args:
        success: 是否清理成功
        task_id: 业务任务 ID
        previous_status: 清理前状态
        cleanup_status: 清理后的状态
        stale_for_seconds: 任务卡住时长（秒）
        runtime_visible: Celery runtime 中是否仍能观察到该任务
        message: 清理结果说明
    """
    success: bool = Field(..., description="是否清理成功")
    task_id: str = Field(..., description="业务任务 ID")
    previous_status: str = Field(..., description="清理前状态")
    cleanup_status: str = Field(..., description="清理后状态")
    stale_for_seconds: Optional[float] = Field(None, description="任务卡住时长（秒）")
    runtime_visible: Optional[bool] = Field(None, description="Celery runtime 中是否仍能观察到该任务")
    cleanup_mode: str = Field(..., description="清理模式：safe 或 force")
    message: str = Field(..., description="清理结果说明")


class CeleryTaskCleanupBatchResponse(BaseModel):
    """
    批量卡住任务清理结果

    Args:
        scanned: 本次扫描的候选任务数量
        cleaned: 成功清理数量
        skipped: 跳过数量
        failed: 失败数量
        task_ids: 本次处理涉及的任务 ID 列表
        message: 批量清理结果说明
    """
    scanned: int = Field(..., description="本次扫描的候选任务数量")
    cleaned: int = Field(..., description="成功清理数量")
    skipped: int = Field(..., description="跳过数量")
    failed: int = Field(..., description="失败数量")
    task_ids: List[str] = Field(default_factory=list, description="本次处理涉及的任务 ID 列表")
    cleanup_mode: str = Field(..., description="清理模式：safe 或 force")
    message: str = Field(..., description="批量清理结果说明")


# ============================================================
# Celery Worker 相关
# ============================================================

class CeleryWorkerInfo(BaseModel):
    """
    Celery Worker 信息

    Args:
        hostname: Worker 主机名
        status: Worker 状态（online/offline）
        active_tasks: 当前活跃任务数
        processed_tasks: 已处理任务总数
    """
    hostname: str = Field(..., description="Worker 主机名")
    status: str = Field(..., description="Worker 状态")
    active_tasks: int = Field(..., description="当前活跃任务数")
    processed_tasks: Optional[int] = Field(None, description="已处理任务总数")
    last_seen_at: Optional[str] = Field(None, description="最近 heartbeat 时间")
    source: str = Field("inspect", description="数据来源：inspect 或 heartbeat")


class CeleryWorkerListResponse(BaseModel):
    """
    Celery Worker 列表响应

    Args:
        workers: Worker 列表
        total: 总数
    """
    workers: List[CeleryWorkerInfo] = Field(..., description="Worker 列表")
    total: int = Field(..., description="总数")
