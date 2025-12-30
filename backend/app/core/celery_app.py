"""
Celery 应用配置

用于异步日志队列处理，完全解耦日志写入和主流程。

架构：
- FastAPI 应用：将日志放入本地缓冲区，批量发送到 Celery
- Celery Worker：独立进程，批量写入数据库
- Redis：作为消息队列 broker 和 result backend

优势：
- 主应用不占用数据库连接
- 独立的 Worker 进程和连接池
- 支持任务重试和故障恢复
"""
from celery import Celery
from app.config.settings import settings

# 构建 Redis URL（支持 Upstash 等云服务的完整 URL，或根据配置构建）
redis_url = settings.get_redis_url

# 检测是否使用 TLS/SSL（rediss:// 协议）
use_ssl = redis_url.startswith("rediss://")

# 如果使用 rediss://，Celery 要求在 URL 中包含 ssl_cert_reqs 参数
if use_ssl and "ssl_cert_reqs" not in redis_url:
    # 添加 ssl_cert_reqs 查询参数
    separator = "&" if "?" in redis_url else "?"
    redis_url = f"{redis_url}{separator}ssl_cert_reqs=required"

# 创建 Celery 应用
celery_app = Celery(
    "roadmap_agent",
    broker=redis_url,
    backend=redis_url,
)

# 配置任务支持
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # 批量处理配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # 任务路由配置（不同任务类型使用不同队列）
    task_routes={
        "app.tasks.log_tasks.batch_write_logs": {"queue": "logs"},
        "app.tasks.content_generation_tasks.*": {"queue": "content_generation"},
        "app.tasks.content_retry_tasks.*": {"queue": "content_generation"},
        "roadmap_generation.*": {"queue": "roadmap_workflow"},
        "workflow_resume.*": {"queue": "roadmap_workflow"},
    },
    # Worker 配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=500,  # 每 500 个任务重启进程（加快资源清理）
    # 任务超时配置（全局默认值，特定任务可覆盖）
    task_time_limit=600,  # 10 分钟硬超时
    task_soft_time_limit=540,  # 9 分钟软超时
    # Redis Backend 超时和连接配置
    # 注意：Upstash Redis（TLS 连接）不支持某些低级别 socket 选项
    result_backend_transport_options={
        "socket_timeout": 10,  # Socket 操作超时 10 秒
        "socket_connect_timeout": 10,  # 连接超时 10 秒
        "socket_keepalive": True,  # 启用 TCP keepalive
        "retry_on_timeout": True,  # 超时时自动重试
        "health_check_interval": 30,  # 健康检查间隔 30 秒
        "max_connections": 50,  # 连接池最大连接数
    },
    # Broker 传输选项（与 backend 相同的配置）
    broker_transport_options={
        "socket_timeout": 10,
        "socket_connect_timeout": 10,
        "socket_keepalive": True,
        "retry_on_timeout": True,
        "health_check_interval": 30,
        "max_connections": 50,
    },
    # 结果存储配置
    result_expires=3600,  # 结果过期时间 1 小时（减少 Redis 存储压力）
    result_backend_always_retry=True,  # 结果后端操作失败时自动重试
    # 自动发现任务模块
    imports=(
        "app.tasks.log_tasks",
        "app.tasks.content_generation_tasks",
        "app.tasks.content_retry_tasks",
        "app.tasks.roadmap_generation_tasks",
        "app.tasks.workflow_resume_tasks",
    ),
)

