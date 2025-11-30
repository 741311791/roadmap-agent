"""
OpenTelemetry 追踪工具
"""
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import structlog

from app.config.settings import settings

logger = structlog.get_logger()

_tracer_provider: Optional[TracerProvider] = None


def setup_tracing():
    """初始化 OpenTelemetry 追踪"""
    global _tracer_provider
    
    if not settings.OTEL_ENABLED:
        logger.info("tracing_disabled")
        return
    
    # 创建资源
    resource = Resource.create({
        "service.name": "roadmap-backend",
        "service.version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    })
    
    # 创建 TracerProvider
    _tracer_provider = TracerProvider(resource=resource)
    
    # 配置导出器
    if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        # 使用 OTLP 导出器
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        )
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info("tracing_otlp_enabled", endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
    else:
        # 使用控制台导出器（开发环境）
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("tracing_console_enabled")
    
    # 设置全局 TracerProvider
    trace.set_tracer_provider(_tracer_provider)
    
    logger.info("tracing_initialized")


def get_tracer(name: str):
    """
    获取 Tracer 实例
    
    Args:
        name: Tracer 名称（通常是模块名）
        
    Returns:
        Tracer 实例
    """
    if not settings.OTEL_ENABLED:
        # 返回 NoOpTracer（不执行任何操作）
        return trace.NoOpTracer()
    
    return trace.get_tracer(name)


def shutdown_tracing():
    """关闭追踪"""
    global _tracer_provider
    
    if _tracer_provider:
        _tracer_provider.shutdown()
        logger.info("tracing_shutdown")

