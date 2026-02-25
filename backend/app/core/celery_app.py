"""
Celery 应用配置

用于异步任务处理。

架构特点：
- FastAPI 应用：将任务提交到 Celery
- Celery Worker：独立进程，执行异步任务
- Redis：作为消息队列 broker 和 result backend
- 单一队列（default）：所有任务统一管理，简化部署

Worker 进程初始化：
- Celery prefork 模式下，子进程继承父进程的全局状态
- 在 worker_process_init 信号中重置必要的进程级资源
- 确保每个子进程使用独立的数据库连接和事件循环
"""
# ✅ Celery Worker 独立进程需要初始化日志系统
# 这会在 Celery 主进程启动时执行一次（父进程）
from app.config.logging_config import setup_logging
setup_logging()

from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown, task_failure, task_retry
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
    # Worker 连接丢失时取消任务，防止重复执行
    worker_cancel_long_running_tasks_on_connection_loss=True,
    # 批量处理配置
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # 任务路由配置
    task_routes={
        "generate_all_content": {"queue": "content_generation"},
        "content.regenerate_single": {"queue": "content_generation"},  # 单 Concept 重新生成
    },
    # 队列定义
    task_queues={
        "celery": {"exchange": "celery", "routing_key": "celery"},  # 默认队列
        "content_generation": {"exchange": "content_generation", "routing_key": "content_generation"},  # 内容生成队列
    },
    # Worker 配置
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=500,  # 每 500 个任务重启进程（加快资源清理）
    # 连接池配置：禁用 Broker 连接池，让每次连接都直接建立新连接
    # 这样在连接被网络层强制断开后，Celery 能立即重新建立连接，而不是从池中
    # 取出一个已经失效的连接。设为 1 表示只保持一个连接（而非池化）
    broker_pool_limit=1,
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
        # visibility_timeout 必须大于最长任务的执行时间
        # 内容生成任务（generate_all_content）最长可达数十分钟
        # 设为 2 小时（7200s），确保长任务不会因超时被重新入队
        # 同时避免 worker 崩溃后任务卡死 1 小时的默认问题
        "visibility_timeout": 7200,
    },
    # ============================================================
    # Broker 连接重试配置（关键：防止空闲时 Broker 连接被网络层关闭后无法恢复）
    # 
    # 问题根因：Celery Worker 空闲（队列无任务）时，Broker 的 TCP 连接长时间无
    # 实际数据交互，NAT/防火墙/路由器等网络中间层会强制关闭该 TCP 连接（通常在
    # 数分钟到30分钟不等）。当 Worker 再次尝试与 Broker 通信时，发现套接字已
    # 断开，触发 BrokenPipeError (Errno 32)。
    #
    # 以下配置确保 Broker 连接断开后能快速自动重连：
    # ============================================================
    broker_connection_retry=True,           # 连接断开后自动重试（默认 True，明确声明）
    broker_connection_retry_on_startup=True, # 启动时连接失败也重试
    broker_connection_max_retries=None,      # 无限重试（None = 永不放弃）
    broker_connection_timeout=10,            # 单次连接超时 10 秒
    # 心跳配置：让 Worker 定期向 Broker 发送心跳，防止空闲连接被网络设备切断
    # 注意：Redis transport 不支持 AMQP 协议的 heartbeat，
    # 实际依赖 health_check_interval + socket_keepalive 来维持连接
    broker_heartbeat=None,                   # Redis transport 不使用 AMQP heartbeat
    # 结果存储配置
    result_expires=3600,  # 结果过期时间 1 小时（减少 Redis 存储压力）
    result_backend_always_retry=True,  # 结果后端操作失败时自动重试
    # 自动发现任务模块
    imports=(
        "app.tasks.log_tasks",
        "app.tasks.roadmap_generation_tasks",
        "app.tasks.workflow_resume_tasks",
        "app.tasks.cover_image_tasks",
        "app.tasks.maintenance_tasks",
        "app.tasks.content_utils",  # 内容重试任务
        "app.tasks.tavily_cache_tasks",  # Tavily Key 缓存任务
        "app.tasks.assessment_initialization_tasks",  # 测验题初始化任务
        "app.tasks.capability_analysis_tasks",  # 技术能力分析任务
        "app.tasks.content_generation_tasks",  # ✅ 内容生成任务
    ),
)


# ============================================================
# Worker 进程初始化钩子
# ============================================================
@worker_process_init.connect
def on_worker_process_init(**kwargs):
    """
    Worker 子进程初始化钩子（重构版 - 持久事件循环）
    
    Celery prefork 模式下，子进程通过 fork() 创建，继承父进程的内存空间。
    必须重置以下进程级资源：
    1. ✅ 创建持久的事件循环（避免每次任务都创建新循环）
    2. 数据库连接引擎（避免跨进程共享连接）
    3. PostgreSQL 连接池（避免 SIGSEGV 段错误）
    4. 第三方库状态（如 litellm 异步日志）
    
    关键修复：
    - 使用 EventLoopManager 创建持久的事件循环
    - 避免 asyncio 原语（Lock、Event等）跨循环使用的问题
    - 符合 asyncio 最佳实践（长期运行的应用应该只有一个事件循环）
    
    参考：
    - https://docs.celeryq.dev/en/stable/userguide/signals.html#worker-process-init
    - https://docs.python.org/3/library/asyncio-eventloop.html#asyncio-multithreading
    """
    from app.config.logging_config import setup_logging
    import structlog
    
    # 步骤1: 子进程重新初始化日志系统
    setup_logging()
    logger = structlog.get_logger()
    
    try:
        # ✅ 步骤2: 创建持久的事件循环（关键修复）
        # 替代原来每次任务都创建新循环的做法
        from app.tasks.event_loop_manager import setup_event_loop
        setup_event_loop()
        logger.info("worker_persistent_event_loop_created")
        
        # 步骤3: 重置数据库引擎缓存
        # 强制子进程创建新的连接，避免跨进程共享
        from app.db.session import reset_engine_cache
        reset_engine_cache()
        
        try:
            from app.db.celery_session import reset_celery_engine_cache
            reset_celery_engine_cache()
        except ImportError:
            pass
        
        logger.info("worker_db_engine_reset")
        
        # 步骤4: 重新初始化 OrchestratorFactory（Fork 安全）
        # 
        # ⚠️ 重要：AsyncConnectionPool 不能跨进程共享
        # OrchestratorFactory.initialize() 已包含 Fork 检测逻辑：
        # - 自动检测进程 ID 变化
        # - 清理父进程的资源引用
        # - 在子进程中创建新的连接池
        #
        # ⚠️ 关键修复：必须在 _worker_loop（后台事件循环）中初始化
        # 原因：psycopg 的 AsyncConnectionPool 将 socket 注册到创建时的 event loop
        # 如果用 asyncio.get_event_loop()（主线程 loop）初始化，而任务通过
        # run_async_in_worker_loop 在后台 _worker_loop 中执行，
        # socket I/O 事件无法被后台 loop 感知，导致 psycopg OperationalError: timeout
        try:
            from app.core.orchestrator_factory import OrchestratorFactory
            from app.tasks.event_loop_manager import run_async_in_worker_loop
            
            # ✅ 在 _worker_loop 中初始化，确保 AsyncConnectionPool 绑定到正确的 loop
            run_async_in_worker_loop(OrchestratorFactory.initialize())
            
            logger.info("worker_orchestrator_factory_initialized")
            
        except Exception as e:
            logger.error(
                "worker_orchestrator_factory_reset_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            # 初始化失败应该让进程退出，避免后续任务执行时崩溃
            raise
        
        # 步骤5: 禁用 litellm 异步日志
        # litellm 的异步日志队列绑定到父进程 event loop
        # 简单禁用即可，不影响功能
        try:
            import litellm
            litellm.disable_async_logging = True
            logger.debug("worker_litellm_async_logging_disabled")
        except Exception as e:
            # litellm 配置失败不影响 Worker 启动
            logger.debug(
                "worker_litellm_config_skipped",
                error=str(e),
            )
        
        # 打印初始化完成日志
        logger.info(
            "worker_process_init_completed",
            db_host=settings.POSTGRES_HOST,
            db_name=settings.POSTGRES_DB,
            event_loop_model="persistent",
        )
        
    except Exception as e:
        logger.error(
            "worker_process_init_failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise  # 初始化失败应该让进程退出


@worker_process_shutdown.connect
def on_worker_process_shutdown(**kwargs):
    """
    Worker 子进程关闭钩子
    
    在 Worker 进程关闭前清理资源，包括：
    1. 停止持久的事件循环
    2. 关闭 OrchestratorFactory 连接池
    
    参考：
    - https://docs.celeryq.dev/en/stable/userguide/signals.html#worker-process-shutdown
    """
    import structlog
    logger = structlog.get_logger()
    
    try:
        # 步骤1: 清理持久的事件循环
        from app.tasks.event_loop_manager import cleanup_event_loop
        cleanup_event_loop()
        logger.info("worker_event_loop_cleaned_up")
        
        # 步骤2: 清理 OrchestratorFactory
        try:
            from app.core.orchestrator_factory import OrchestratorFactory
            if OrchestratorFactory._initialized:
                # 注意：cleanup 方法是异步的，但在 shutdown 时我们无法运行异步代码
                # 连接池会在进程退出时自动关闭，这里只是标记为未初始化
                OrchestratorFactory._initialized = False
                logger.info("worker_orchestrator_factory_marked_for_cleanup")
        except Exception as e:
            logger.warning(
                "worker_orchestrator_factory_cleanup_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
        
        logger.info("worker_process_shutdown_completed")
        
    except Exception as e:
        logger.error(
            "worker_process_shutdown_failed",
            error=str(e),
            error_type=type(e).__name__,
        )


# ============================================================
# Celery 错误信号处理器（全局异常捕获）
# ============================================================
@task_failure.connect
def on_task_failure(sender=None, task_id=None, exception=None, **kwargs):
    """
    Celery 任务失败信号处理器
    
    捕获所有未被 @safe_task 装饰器处理的任务异常。
    当任务抛出异常且未被捕获时，此信号会被触发。
    
    Args:
        sender: 任务实例
        task_id: Celery 任务 ID
        exception: 异常对象
        **kwargs: 其他信号参数
    """
    from app.core.celery_error_handler import handle_task_failure
    handle_task_failure(sender, task_id, exception, **kwargs)


@task_retry.connect
def on_task_retry(sender=None, task_id=None, **kwargs):
    """
    Celery 任务重试信号处理器
    
    当任务重试时，此信号会被触发。
    用于记录重试事件，方便排查问题。
    
    Args:
        sender: 任务实例
        task_id: Celery 任务 ID
        **kwargs: 其他信号参数（包含 reason、einfo 等）
    """
    from app.core.celery_error_handler import handle_task_retry
    handle_task_retry(sender, task_id, **kwargs)


# ============================================================
# Celery Beat 定时任务配置
# ============================================================
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    # 每天凌晨 3 点清理旧的 Checkpoint
    'cleanup-old-checkpoints': {
        'task': 'maintenance.cleanup_old_checkpoints',
        'schedule': crontab(hour=3, minute=0),
    },
    # 每小时监控 Checkpoint 表大小
    'monitor-checkpoint-size': {
        'task': 'maintenance.monitor_checkpoint_size',
        'schedule': crontab(minute=0),  # 每小时整点执行
    },
    # ✅ 每 5 分钟刷新 Tavily API Key 缓存
    'refresh-tavily-key-cache': {
        'task': 'tavily_cache.refresh_keys',
        'schedule': 300.0,  # 每 5 分钟（秒）
    },
    # ✅ 每小时清理失效的 Tavily Key
    'cleanup-expired-tavily-keys': {
        'task': 'tavily_cache.cleanup_expired',
        'schedule': crontab(minute=15),  # 每小时的第 15 分钟
    },
}
