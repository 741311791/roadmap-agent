"""
structlog 配置
"""
import logging
import sys
import structlog
from structlog.types import EventDict

from app.config.settings import settings


def add_app_context(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """添加应用全局上下文"""
    event_dict["environment"] = settings.ENVIRONMENT
    event_dict["service"] = "roadmap-backend"
    return event_dict


def setup_logging():
    """初始化日志系统"""
    
    # 配置标准库 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    )
    
    # 禁用 SQLAlchemy 引擎日志（防止输出大量 SQL 语句）
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)
    
    # 禁用 httpx 和 httpcore 的调试日志（防止 HTTP 请求日志过多）
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            add_app_context,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # 配置 uvicorn 日志
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        logger = logging.getLogger(logger_name)
        logger.handlers = [logging.StreamHandler(sys.stdout)]
        logger.propagate = False

