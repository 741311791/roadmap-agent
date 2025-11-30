"""
MinIO Bucket 初始化模块

在应用启动时自动创建所需的 bucket（如果不存在）。
"""
import asyncio
from minio import Minio
from minio.error import S3Error
import structlog
from urllib.parse import urlparse

from app.config.settings import settings

logger = structlog.get_logger()


def _get_minio_client() -> Minio:
    """创建 MinIO 客户端"""
    parsed = urlparse(settings.S3_ENDPOINT_URL)
    endpoint = parsed.netloc or parsed.path
    secure = parsed.scheme == "https"
    
    return Minio(
        endpoint=endpoint,
        access_key=settings.S3_ACCESS_KEY_ID,
        secret_key=settings.S3_SECRET_ACCESS_KEY,
        secure=secure,
    )


async def ensure_bucket_exists() -> bool:
    """
    确保 MinIO bucket 存在，如不存在则创建。
    
    Returns:
        bool: 是否成功（True 表示 bucket 已存在或创建成功）
    """
    bucket_name = settings.S3_BUCKET_NAME
    
    try:
        client = _get_minio_client()
        
        # 检查 bucket 是否存在
        bucket_exists = await asyncio.to_thread(
            client.bucket_exists,
            bucket_name
        )
        
        if bucket_exists:
            logger.info(
                "minio_bucket_exists",
                bucket=bucket_name,
                endpoint=settings.S3_ENDPOINT_URL,
            )
            return True
        else:
            # Bucket 不存在，创建它
            logger.info(
                "minio_bucket_creating",
                bucket=bucket_name,
                endpoint=settings.S3_ENDPOINT_URL,
            )
            
            await asyncio.to_thread(
                client.make_bucket,
                bucket_name
            )
            
            logger.info(
                "minio_bucket_created",
                bucket=bucket_name,
                endpoint=settings.S3_ENDPOINT_URL,
            )
            return True
    
    except S3Error as e:
        logger.error(
            "minio_init_failed",
            bucket=bucket_name,
            endpoint=settings.S3_ENDPOINT_URL,
            error=str(e),
            error_code=e.code if hasattr(e, 'code') else None,
        )
        # 不抛出异常，允许应用继续启动（可能 MinIO 服务暂时不可用）
        return False
    
    except Exception as e:
        logger.error(
            "minio_init_failed",
            bucket=bucket_name,
            endpoint=settings.S3_ENDPOINT_URL,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False


async def check_minio_connection() -> bool:
    """
    检查 MinIO 连接是否正常。
    
    Returns:
        bool: 连接是否成功
    """
    try:
        client = _get_minio_client()
        
        # 尝试列出 bucket（验证连接）
        buckets = await asyncio.to_thread(client.list_buckets)
        
        logger.info(
            "minio_connection_ok",
            endpoint=settings.S3_ENDPOINT_URL,
            buckets_count=len(buckets) if buckets else 0,
        )
        return True
    
    except S3Error as e:
        logger.warning(
            "minio_connection_failed",
            endpoint=settings.S3_ENDPOINT_URL,
            error=str(e),
            error_code=e.code if hasattr(e, 'code') else None,
        )
        return False
    
    except Exception as e:
        logger.warning(
            "minio_connection_failed",
            endpoint=settings.S3_ENDPOINT_URL,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False
