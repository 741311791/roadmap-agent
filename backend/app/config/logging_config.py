"""
structlog 配置（生产级优化版）

优化：
- 错误堆栈简化（只保留项目代码）
- Agent 输出截断（前50字符）
- 日志数据清理（移除冗余信息）
- 根据环境变量调整日志级别
- 错误日志文件收集（可选，仅本地环境）
- 智能格式选择：
  * 开发/测试环境：彩色控制台格式（可读性优先）
  * 生产环境：JSON 格式（便于日志收集系统解析）
- 第三方库日志降噪：
  * SQLAlchemy, botocore, httpx, litellm, celery 等
  * 只记录 WARNING 及以上级别，避免日志污染
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
import structlog
from structlog.types import EventDict

from app.config.settings import settings


def add_app_context(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """添加应用全局上下文"""
    event_dict["environment"] = settings.ENVIRONMENT
    event_dict["service"] = "roadmap-backend"
    return event_dict


def sanitize_event_dict(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """
    清理日志事件数据
    
    功能：
    - 截断长字符串（Agent 输出、用户输入等）
    - 简化嵌套结构
    - 减少日志噪音
    """
    from app.utils.log_formatters import sanitize_log_data
    
    # 只处理 event_dict 中的非系统字段
    system_keys = {
        "event", "level", "logger", "timestamp", 
        "environment", "service", "exc_info"
    }
    
    user_data = {k: v for k, v in event_dict.items() if k not in system_keys}
    sanitized = sanitize_log_data(user_data)
    
    # 保留系统字段，更新用户数据
    result = {k: v for k, v in event_dict.items() if k in system_keys}
    result.update(sanitized)
    
    return result


def format_exc_info_compact(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """
    简化异常堆栈输出
    
    只保留：
    - 异常类型和消息
    - 项目代码堆栈（去除系统库）
    - 最近5层调用
    """
    import sys
    from app.utils.log_formatters import format_exception_compact
    
    exc_info = event_dict.pop("exc_info", None)
    
    # ⚠️ 关键修复：提前处理 exc_info=True 的情况
    # structlog 不会自动转换 bool 为异常信息，必须在此处主动调用 sys.exc_info()
    if isinstance(exc_info, bool) and exc_info:
        exc_info = sys.exc_info()
    
    # 验证异常信息有效性
    if exc_info and exc_info != (None, None, None):
        try:
            # 简化堆栈
            event_dict["exception"] = format_exception_compact(exc_info)
        except Exception as format_error:
            # 🛡️ 防御性编程：日志处理器自身不应该抛出异常
            event_dict["exception_format_error"] = str(format_error)
    
    return event_dict


def _setup_error_log_file():
    """
    设置错误日志文件（仅在启用时）
    
    功能：
    - 仅收集 WARNING、ERROR、CRITICAL 级别日志
    - 可读性优先的纯文本格式
    - 自动日志轮转（单文件最大10MB）
    - 不保留备份文件（backupCount=0）
    
    配置来源：
    - settings.ERROR_LOG_FILE_PATH: 日志文件路径
    - settings.ERROR_LOG_FILE_MAX_SIZE: 单文件最大大小
    """
    # 创建日志目录
    log_path = Path(settings.ERROR_LOG_FILE_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 创建 RotatingFileHandler
    error_handler = RotatingFileHandler(
        filename=log_path,
        maxBytes=settings.ERROR_LOG_FILE_MAX_SIZE,
        backupCount=0,  # 不保留备份文件
        encoding="utf-8"
    )
    
    # 仅记录 WARNING 及以上级别
    error_handler.setLevel(logging.WARNING)
    
    # 使用可读性优先的格式
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    error_handler.setFormatter(formatter)
    
    # 添加到 root logger
    logging.getLogger().addHandler(error_handler)
    
    # 记录启用信息
    logger = structlog.get_logger(__name__)
    logger.info(
        "error_log_file_enabled",
        log_file=str(log_path),
        max_size_mb=settings.ERROR_LOG_FILE_MAX_SIZE / (1024 * 1024),
        min_level="WARNING"
    )


def setup_logging():
    """初始化日志系统（生产级优化版）"""
    
    # ===== 根据环境设置日志级别 =====
    if settings.ENVIRONMENT == "production":
        log_level = logging.WARNING  # 生产环境：只记录警告和错误
    elif settings.ENVIRONMENT == "testing":
        log_level = logging.WARNING  # 测试环境：只记录警告和错误
    elif settings.DEBUG:
        log_level = logging.DEBUG    # 调试模式：记录所有详细信息
    else:
        log_level = logging.INFO     # 开发环境：记录信息级别
    
    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # ===== 禁用第三方库的详细日志 =====
    # SQLAlchemy（防止输出大量 SQL 语句）
    logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.orm").setLevel(logging.ERROR)
    
    # HTTP 客户端（防止 HTTP 请求日志过多）
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    # AWS SDK（防止 S3/boto 详细日志）
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("aiobotocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("s3transfer").setLevel(logging.WARNING)
    
    # LiteLLM（防止 LLM 调用详细日志）
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    logging.getLogger("litellm").setLevel(logging.WARNING)
    
    # Celery（减少 Worker 日志）
    logging.getLogger("celery").setLevel(logging.WARNING)
    logging.getLogger("celery.worker").setLevel(logging.INFO)
    logging.getLogger("celery.app.trace").setLevel(logging.WARNING)
    
    # 其他第三方库
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # ===== 配置 structlog（优化版） =====
    # 根据环境选择输出格式
    if settings.ENVIRONMENT == "production":
        # 生产环境：JSON 格式（便于日志收集系统解析）
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            add_app_context,
            sanitize_event_dict,
            format_exc_info_compact,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),  # JSON 格式
        ]
    else:
        # 开发/测试环境：彩色控制台格式（可读性优先）
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            add_app_context,
            sanitize_event_dict,
            format_exc_info_compact,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(  # ✅ 彩色控制台格式
                colors=True,  # 启用颜色
                exception_formatter=structlog.dev.plain_traceback,  # 清晰的异常格式
            ),
        ]
    
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # ===== 配置 uvicorn 日志 =====
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.handlers = [logging.StreamHandler(sys.stdout)]
        logger.propagate = False
        # uvicorn.access 可以更安静
        if logger_name == "uvicorn.access":
            logger.setLevel(logging.WARNING)
    
    # ===== 配置错误日志文件（仅在启用时）=====
    if settings.ENABLE_ERROR_LOG_FILE:
        _setup_error_log_file()

