"""
Prometheus 指标定义

集中管理所有 Prometheus 监控指标，包括：
- HTTP 请求计数器
- HTTP 响应时间直方图
- 数据库连接池指标
- Celery 任务指标
"""
from prometheus_client import Counter, Histogram, Gauge, Info, REGISTRY

# ============================================================
# 指标缓存 - 防止重复注册
# ============================================================
_metrics_cache = {}

def _get_or_create_counter(name: str, description: str, labels: list) -> Counter:
    """获取或创建 Counter 指标"""
    if name not in _metrics_cache:
        try:
            _metrics_cache[name] = Counter(name, description, labels)
        except ValueError:
            # 如果已经注册，从 registry 中获取
            for collector in REGISTRY._collector_to_names:
                if hasattr(collector, "_name") and collector._name == name:
                    _metrics_cache[name] = collector
                    break
    return _metrics_cache[name]

def _get_or_create_histogram(name: str, description: str, labels: list) -> Histogram:
    """获取或创建 Histogram 指标"""
    if name not in _metrics_cache:
        try:
            _metrics_cache[name] = Histogram(name, description, labels)
        except ValueError:
            # 如果已经注册，从 registry 中获取
            for collector in REGISTRY._collector_to_names:
                if hasattr(collector, "_name") and collector._name == name:
                    _metrics_cache[name] = collector
                    break
    return _metrics_cache[name]

def _get_or_create_gauge(name: str, description: str, labels: list) -> Gauge:
    """获取或创建 Gauge 指标"""
    if name not in _metrics_cache:
        try:
            _metrics_cache[name] = Gauge(name, description, labels)
        except ValueError:
            # 如果已经注册，从 registry 中获取
            for collector in REGISTRY._collector_to_names:
                if hasattr(collector, "_name") and collector._name == name:
                    _metrics_cache[name] = collector
                    break
    return _metrics_cache[name]

def _get_or_create_info(name: str, description: str) -> Info:
    """获取或创建 Info 指标"""
    if name not in _metrics_cache:
        try:
            _metrics_cache[name] = Info(name, description)
        except ValueError:
            # 如果已经注册，从 registry 中获取
            for collector in REGISTRY._collector_to_names:
                if hasattr(collector, "_name") and collector._name == name:
                    _metrics_cache[name] = collector
                    break
    return _metrics_cache[name]

# ============================================================
# HTTP 请求指标
# ============================================================

REQUEST_COUNTER = _get_or_create_counter(
    "http_requests_total",
    "Total HTTP requests",
    ["app_name", "method", "path", "status_code"]
)

RESPONSE_TIME_HISTOGRAM = _get_or_create_histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["app_name", "method", "path"]
)

# ============================================================
# 数据库连接池指标
# ============================================================

DB_POOL_SIZE = _get_or_create_gauge(
    "db_pool_size",
    "Current database connection pool size",
    ["pool_name"]
)

DB_POOL_CHECKED_OUT = _get_or_create_gauge(
    "db_pool_checked_out_connections",
    "Number of connections currently checked out from the pool",
    ["pool_name"]
)

DB_POOL_OVERFLOW = _get_or_create_gauge(
    "db_pool_overflow_connections",
    "Number of connections in overflow (beyond pool_size)",
    ["pool_name"]
)

DB_POOL_CHECKED_IN = _get_or_create_gauge(
    "db_pool_checked_in_connections",
    "Number of connections currently checked in (idle) in the pool",
    ["pool_name"]
)

# ============================================================
# Celery 任务指标
# ============================================================

CELERY_TASK_COUNTER = _get_or_create_counter(
    "celery_tasks_total",
    "Total number of Celery tasks",
    ["task_name", "status"]  # status: success, failure, retry
)

CELERY_TASK_DURATION = _get_or_create_histogram(
    "celery_task_duration_seconds",
    "Celery task execution duration in seconds",
    ["task_name"]
)

# ============================================================
# Redis 指标
# ============================================================

REDIS_CACHE_HIT_COUNTER = _get_or_create_counter(
    "redis_cache_hits_total",
    "Total number of Redis cache hits",
    ["cache_key_prefix"]
)

REDIS_CACHE_MISS_COUNTER = _get_or_create_counter(
    "redis_cache_misses_total",
    "Total number of Redis cache misses",
    ["cache_key_prefix"]
)

# ============================================================
# 应用信息
# ============================================================

APP_INFO = _get_or_create_info(
    "app_info",
    "Application information"
)

# 设置应用信息（在启动时调用）
def set_app_info(version: str = "1.0.0", environment: str = "development"):
    """
    设置应用信息指标
    
    Args:
        version: 应用版本
        environment: 运行环境
    """
    APP_INFO.info({
        "version": version,
        "environment": environment,
        "app_name": "roadmap_agent",
    })

