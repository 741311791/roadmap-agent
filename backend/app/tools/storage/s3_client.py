"""
MinIO 异步存储客户端（使用官方 minio SDK）

支持 MinIO 对象存储的上传和下载操作。
"""
import asyncio
from datetime import timedelta
from io import BytesIO
from minio import Minio
from minio.error import S3Error
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from urllib.parse import urlparse

from app.tools.base import BaseTool
from app.models.domain import S3UploadRequest, S3UploadResult, S3DownloadRequest, S3DownloadResult
from app.config.settings import settings

logger = structlog.get_logger()


class S3StorageTool(BaseTool[S3UploadRequest, S3UploadResult]):
    """MinIO 对象存储工具"""
    
    def __init__(self):
        super().__init__(tool_id="minio_storage_v1")
        
        # 解析端点 URL
        parsed = urlparse(settings.S3_ENDPOINT_URL)
        self.endpoint = parsed.netloc or parsed.path
        self.secure = parsed.scheme == "https"
        
        # 创建 MinIO 客户端
        self.client = Minio(
            endpoint=self.endpoint,
            access_key=settings.S3_ACCESS_KEY_ID,
            secret_key=settings.S3_SECRET_ACCESS_KEY,
            secure=self.secure,
        )
        
        self.default_bucket = settings.S3_BUCKET_NAME
        
        logger.debug(
            "minio_client_initialized",
            endpoint=self.endpoint,
            secure=self.secure,
            bucket=self.default_bucket,
        )
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        retry=retry_if_exception_type(S3Error),
        reraise=True,
    )
    async def execute(self, input_data: S3UploadRequest) -> S3UploadResult:
        """
        上传内容到 MinIO
        
        Args:
            input_data: 上传请求
            
        Returns:
            上传结果
        """
        bucket = input_data.bucket or self.default_bucket
        
        try:
            # 将内容编码为字节
            content_bytes = input_data.content.encode("utf-8")
            size_bytes = len(content_bytes)
            
            # 使用 BytesIO 包装字节数据
            data_stream = BytesIO(content_bytes)
            
            # 在线程池中执行同步的 MinIO 操作
            await asyncio.to_thread(
                self.client.put_object,
                bucket_name=bucket,
                object_name=input_data.key,
                data=data_stream,
                length=size_bytes,
                content_type=input_data.content_type,
            )
            
            # 生成预签名 URL（有效期 7 天）
            url = await asyncio.to_thread(
                self.client.presigned_get_object,
                bucket_name=bucket,
                object_name=input_data.key,
                expires=timedelta(days=7),
            )
            
            logger.info(
                "minio_upload_success",
                key=input_data.key,
                bucket=bucket,
                size_bytes=size_bytes,
            )
            
            return S3UploadResult(
                success=True,
                url=url,
                key=input_data.key,
                size_bytes=size_bytes,
                etag=None,  # MinIO SDK 不直接返回 ETag
            )
            
        except S3Error as e:
            logger.error(
                "minio_upload_failed",
                key=input_data.key,
                bucket=bucket,
                error=str(e),
                error_code=e.code if hasattr(e, 'code') else None,
            )
            raise
        except Exception as e:
            logger.error(
                "minio_upload_failed",
                key=input_data.key,
                bucket=bucket,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        retry=retry_if_exception_type(S3Error),
        reraise=True,
    )
    async def download(self, input_data: S3DownloadRequest) -> S3DownloadResult:
        """
        从 MinIO 下载内容
        
        Args:
            input_data: 下载请求
            
        Returns:
            下载结果
        """
        bucket = input_data.bucket or self.default_bucket
        
        try:
            # 在线程池中执行同步的 MinIO 操作
            response = await asyncio.to_thread(
                self.client.get_object,
                bucket_name=bucket,
                object_name=input_data.key,
            )
            
            # 读取内容
            content_bytes = await asyncio.to_thread(response.read)
            content = content_bytes.decode("utf-8")
            size_bytes = len(content_bytes)
            
            # 获取元数据
            stat = await asyncio.to_thread(
                self.client.stat_object,
                bucket_name=bucket,
                object_name=input_data.key,
            )
            
            # 关闭响应流
            await asyncio.to_thread(response.close)
            await asyncio.to_thread(response.release_conn)
            
            logger.info(
                "minio_download_success",
                key=input_data.key,
                bucket=bucket,
                size_bytes=size_bytes,
            )
            
            return S3DownloadResult(
                success=True,
                content=content,
                key=input_data.key,
                size_bytes=size_bytes,
                content_type=stat.content_type if stat.content_type else None,
                etag=stat.etag if stat.etag else None,
                last_modified=stat.last_modified if stat.last_modified else None,
            )
            
        except S3Error as e:
            logger.error(
                "minio_download_failed",
                key=input_data.key,
                bucket=bucket,
                error=str(e),
                error_code=e.code if hasattr(e, 'code') else None,
            )
            raise
        except Exception as e:
            logger.error(
                "minio_download_failed",
                key=input_data.key,
                bucket=bucket,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
