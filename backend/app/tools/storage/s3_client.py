"""
Cloudflare R2 / S3 异步存储客户端（使用 aioboto3）

支持 S3 兼容对象存储的上传和下载操作。
兼容 Cloudflare R2、AWS S3、MinIO 等。
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import aioboto3
from botocore.exceptions import ClientError
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.tools.base import BaseTool
from app.models.domain import S3UploadRequest, S3UploadResult, S3DownloadRequest, S3DownloadResult
from app.config.settings import settings

logger = structlog.get_logger()


class S3StorageTool(BaseTool[S3UploadRequest, S3UploadResult]):
    """S3 兼容对象存储工具（支持 Cloudflare R2、AWS S3、MinIO）"""
    
    def __init__(self):
        super().__init__(tool_id="s3_storage_v1")
        
        # 创建 aioboto3 会话
        self.session = aioboto3.Session()
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.region = settings.S3_REGION or "auto"
        self.default_bucket = settings.S3_BUCKET_NAME
        
        logger.info(
            "s3_client_initialized",
            endpoint=self.endpoint_url,
            region=self.region,
            bucket=self.default_bucket,
        )
    
    @asynccontextmanager
    async def _get_client(self) -> AsyncGenerator:
        """获取 S3 异步客户端（上下文管理器）"""
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
            region_name=self.region,
        ) as client:
            yield client
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        retry=retry_if_exception_type(ClientError),
        reraise=True,
    )
    async def execute(self, input_data: S3UploadRequest) -> S3UploadResult:
        """
        上传内容到 S3 兼容存储
        
        Args:
            input_data: 上传请求
            
        Returns:
            上传结果
        """
        bucket = input_data.bucket or self.default_bucket
        
        try:
            async with self._get_client() as s3:
                # 将内容编码为字节
                content_bytes = input_data.content.encode("utf-8")
                size_bytes = len(content_bytes)
                
                # 上传对象
                await s3.put_object(
                    Bucket=bucket,
                    Key=input_data.key,
                    Body=content_bytes,
                    ContentType=input_data.content_type,
                )
                
                # 生成预签名 URL（有效期 7 天）
                url = await s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": input_data.key},
                    ExpiresIn=604800,  # 7 天
                )
                
                logger.info(
                    "s3_upload_success",
                    key=input_data.key,
                    bucket=bucket,
                    size_bytes=size_bytes,
                )
                
                return S3UploadResult(
                    success=True,
                    url=url,
                    key=input_data.key,
                    size_bytes=size_bytes,
                    etag=None,  # 可以从 put_object 响应中获取，但暂时不需要
                )
        
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "s3_upload_failed",
                key=input_data.key,
                bucket=bucket,
                error=str(e),
                error_code=error_code,
            )
            raise
        except Exception as e:
            logger.error(
                "s3_upload_failed",
                key=input_data.key,
                bucket=bucket,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=3, max=30),
        retry=retry_if_exception_type(ClientError),
        reraise=True,
    )
    async def download(self, input_data: S3DownloadRequest) -> S3DownloadResult:
        """
        从 S3 兼容存储下载内容
        
        Args:
            input_data: 下载请求
            
        Returns:
            下载结果
        """
        bucket = input_data.bucket or self.default_bucket
        
        try:
            async with self._get_client() as s3:
                # 获取对象
                response = await s3.get_object(
                    Bucket=bucket,
                    Key=input_data.key,
                )
                
                # 读取内容
                async with response["Body"] as stream:
                    content_bytes = await stream.read()
                
                content = content_bytes.decode("utf-8")
                size_bytes = len(content_bytes)
                
                # 获取元数据
                content_type = response.get("ContentType")
                etag = response.get("ETag")
                last_modified = response.get("LastModified")
                
                logger.info(
                    "s3_download_success",
                    key=input_data.key,
                    bucket=bucket,
                    size_bytes=size_bytes,
                )
                
                return S3DownloadResult(
                    success=True,
                    content=content,
                    key=input_data.key,
                    size_bytes=size_bytes,
                    content_type=content_type,
                    etag=etag.strip('"') if etag else None,  # 移除引号
                    last_modified=last_modified,
                )
        
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            logger.error(
                "s3_download_failed",
                key=input_data.key,
                bucket=bucket,
                error=str(e),
                error_code=error_code,
            )
            raise
        except Exception as e:
            logger.error(
                "s3_download_failed",
                key=input_data.key,
                bucket=bucket,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
