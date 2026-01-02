"""
Celery 应用配置

用于异步任务处理，包括日志队列和路线图生成任务。

架构：
- FastAPI 应用：将任务提交到 Celery
- Celery Worker：独立进程，执行异步任务
- Redis：作为消息队列 broker 和 result backend

Worker 进程初始化：
- Celery prefork 模式下，子进程继承父进程的全局状态
- 在 worker_process_init 信号中重置数据库 engine 缓存
- 确保每个子进程使用独立的数据库连接
"""
from celery import Celery
from celery.signals import worker_process_init
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
    # 注意：Railway/Upstash Redis 不支持低级别 socket 选项，移除 socket_keepalive_options
    result_backend_transport_options={
        "socket_timeout": 30,  # Socket 操作超时 30 秒(适配云服务网络延迟)
        "socket_connect_timeout": 10,  # 连接超时 10 秒
        "socket_keepalive": True,  # 启用 TCP keepalive（使用系统默认参数）
        "retry_on_timeout": True,  # 超时时自动重试
        "health_check_interval": 25,  # 健康检查间隔 25 秒(略小于空闲超时)
        "max_connections": 50,  # 连接池最大连接数
    },
    # Broker 传输选项（与 backend 相同的配置）
    broker_transport_options={
        "socket_timeout": 30,  # 与 backend 保持一致
        "socket_connect_timeout": 10,
        "socket_keepalive": True,  # 启用 TCP keepalive（使用系统默认参数）
        "retry_on_timeout": True,
        "health_check_interval": 25,  # 与 backend 保持一致
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


# ============================================================
# Worker 进程初始化钩子（解决数据库连接隔离问题）
# ============================================================
@worker_process_init.connect
def on_worker_process_init(**kwargs):
    """
    Worker 子进程初始化时调用
    
    Celery prefork 模式下，子进程继承父进程的全局变量。
    清空继承的 engine 缓存，强制子进程创建新的数据库连接。
    """
    import structlog
    logger = structlog.get_logger()
    
    try:
        # 重置主 session 模块的 engine 缓存
        from app.db.session import reset_engine_cache
        reset_engine_cache()
        
        # 重置 Celery 专用 session 模块的 engine 缓存（如果存在）
        try:
            from app.db.celery_session import reset_celery_engine_cache
            reset_celery_engine_cache()
        except ImportError:
            pass
        
        logger.info(
            "celery_worker_process_init",
            message="Celery Worker 进程初始化完成，数据库引擎缓存已重置",
        )
    except Exception as e:
        logger.error(
            "celery_worker_process_init_error",
            error=str(e),
            error_type=type(e).__name__,
        )

