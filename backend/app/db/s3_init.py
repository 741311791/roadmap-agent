"""
S3 兼容存储 Bucket 初始化模块

在应用启动时自动创建所需的 bucket（如果不存在）。
支持 Cloudflare R2、AWS S3、MinIO 等 S3 兼容存储。
"""
import aioboto3
from botocore.exceptions import ClientError
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


async def ensure_bucket_exists() -> bool:
    """
    确保 S3 bucket 存在，如不存在则创建。
    
    Returns:
        bool: 是否成功（True 表示 bucket 已存在或创建成功）
    """
    bucket_name = settings.S3_BUCKET_NAME
    
    try:
        session = aioboto3.Session()
        
        async with session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
        ) as s3:
            # 检查 bucket 是否存在
            try:
                await s3.head_bucket(Bucket=bucket_name)
                logger.info(
                    "s3_bucket_exists",
                    bucket=bucket_name,
                    endpoint=settings.S3_ENDPOINT_URL,
                )
                return True
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                
                # 404 表示 bucket 不存在，需要创建
                if error_code == "404":
                    logger.info(
                        "s3_bucket_creating",
                        bucket=bucket_name,
                        endpoint=settings.S3_ENDPOINT_URL,
                    )
                    
                    # 创建 bucket
                    await s3.create_bucket(Bucket=bucket_name)
                    
                    logger.info(
                        "s3_bucket_created",
                        bucket=bucket_name,
                        endpoint=settings.S3_ENDPOINT_URL,
                    )
                    return True
                else:
                    # 其他错误（如权限问题）
                    raise
    
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.error(
            "s3_init_failed",
            bucket=bucket_name,
            endpoint=settings.S3_ENDPOINT_URL,
            error=str(e),
            error_code=error_code,
        )
        # 不抛出异常，允许应用继续启动（可能存储服务暂时不可用）
        return False
    
    except Exception as e:
        logger.error(
            "s3_init_failed",
            bucket=bucket_name,
            endpoint=settings.S3_ENDPOINT_URL,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False


async def check_s3_connection() -> bool:
    """
    检查 S3 连接是否正常。
    
    Returns:
        bool: 连接是否成功
    """
    try:
        session = aioboto3.Session()
        
        async with session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=settings.S3_REGION,
        ) as s3:
            # 尝试列出 bucket（验证连接）
            response = await s3.list_buckets()
            buckets = response.get("Buckets", [])
            
            logger.info(
                "s3_connection_ok",
                endpoint=settings.S3_ENDPOINT_URL,
                buckets_count=len(buckets),
            )
            return True
    
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        logger.warning(
            "s3_connection_failed",
            endpoint=settings.S3_ENDPOINT_URL,
            error=str(e),
            error_code=error_code,
        )
        return False
    
    except Exception as e:
        logger.warning(
            "s3_connection_failed",
            endpoint=settings.S3_ENDPOINT_URL,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False

