# S3 下载功能使用指南

## 概述

S3StorageTool 现在支持文件下载功能，可以从 S3/R2 对象存储中下载文本内容。

## 功能特性

- ✅ 异步下载支持
- ✅ 自动重试机制（最多 3 次，指数退避）
- ✅ 自动 UTF-8 解码
- ✅ 返回元数据（Content-Type、ETag、最后修改时间等）
- ✅ 详细的日志记录

## 域模型

### S3DownloadRequest

```python
class S3DownloadRequest(BaseModel):
    """S3 对象存储下载请求"""
    key: str  # 对象存储路径，如 'roadmaps/{id}/concepts/{cid}/v1.md'
    bucket: Optional[str] = None  # 存储桶名称（默认使用配置）
```

### S3DownloadResult

```python
class S3DownloadResult(BaseModel):
    """S3 下载结果"""
    success: bool  # 下载是否成功
    content: str  # 下载的文本内容
    key: str  # 对象的 Key
    size_bytes: int  # 下载的文件大小
    content_type: Optional[str] = None  # 对象的 Content-Type
    etag: Optional[str] = None  # 对象的 ETag
    last_modified: Optional[datetime] = None  # 对象的最后修改时间
```

## 使用示例

### 基本用法

```python
from app.tools.storage.s3_client import S3StorageTool
from app.models.domain import S3DownloadRequest

# 创建工具实例
s3_tool = S3StorageTool()

# 创建下载请求
download_request = S3DownloadRequest(
    key="test-roadmap/concepts/concept-1/v1.md"
)

# 执行下载
result = await s3_tool.download(download_request)

if result.success:
    print(f"下载成功！")
    print(f"内容长度: {result.size_bytes} 字节")
    print(f"Content-Type: {result.content_type}")
    print(f"内容: {result.content[:100]}...")  # 显示前 100 个字符
else:
    print("下载失败")
```

### 指定存储桶

```python
# 从指定的存储桶下载
download_request = S3DownloadRequest(
    key="tutorials/python-basics.md",
    bucket="my-custom-bucket"
)

result = await s3_tool.download(download_request)
```

### 完整示例（上传然后下载）

```python
from app.tools.storage.s3_client import S3StorageTool
from app.models.domain import S3UploadRequest, S3DownloadRequest

async def upload_and_download_example():
    s3_tool = S3StorageTool()
    
    # 1. 上传内容
    upload_request = S3UploadRequest(
        key="test/sample.md",
        content="# Hello World\n\nThis is a test file.",
        content_type="text/markdown"
    )
    
    upload_result = await s3_tool.execute(upload_request)
    print(f"上传成功: {upload_result.url}")
    
    # 2. 下载内容
    download_request = S3DownloadRequest(
        key="test/sample.md"
    )
    
    download_result = await s3_tool.download(download_request)
    print(f"下载成功，内容: {download_result.content}")
    
    # 验证内容一致
    assert upload_request.content == download_result.content
    print("✅ 内容验证通过！")

# 在异步上下文中运行
# await upload_and_download_example()
```

### 错误处理

```python
from botocore.exceptions import ClientError

async def download_with_error_handling():
    s3_tool = S3StorageTool()
    
    try:
        download_request = S3DownloadRequest(
            key="non-existent-file.md"
        )
        result = await s3_tool.download(download_request)
        print(f"下载成功: {result.content}")
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        
        if error_code == 'NoSuchKey':
            print("❌ 文件不存在")
        elif error_code == 'AccessDenied':
            print("❌ 没有权限访问该文件")
        else:
            print(f"❌ S3 错误: {error_code}")
            
    except UnicodeDecodeError:
        print("❌ 文件编码不是 UTF-8，无法解码")
        
    except Exception as e:
        print(f"❌ 未知错误: {str(e)}")
```

## 在 Agent 中使用

### 在教程生成器中使用

```python
from app.agents.tutorial_generator import TutorialGeneratorAgent
from app.tools.storage.s3_client import S3StorageTool
from app.models.domain import S3DownloadRequest

class TutorialGeneratorAgent(BaseAgent):
    def __init__(self):
        super().__init__()
        self.s3_tool = S3StorageTool()
    
    async def load_existing_tutorial(self, concept_id: str, roadmap_id: str) -> str:
        """加载现有的教程内容"""
        download_request = S3DownloadRequest(
            key=f"{roadmap_id}/concepts/{concept_id}/v1.md"
        )
        
        try:
            result = await self.s3_tool.download(download_request)
            return result.content
        except Exception as e:
            logger.error(
                "failed_to_load_tutorial",
                concept_id=concept_id,
                roadmap_id=roadmap_id,
                error=str(e)
            )
            raise
```

## 性能特性

### 自动重试

下载方法配置了自动重试机制：
- 最多重试 3 次
- 指数退避策略（2 秒、4 秒、8 秒...，最多 10 秒）
- 适用于临时网络故障

### 日志记录

下载操作会记录以下日志：

**成功时：**
```json
{
  "event": "s3_download_success",
  "key": "roadmaps/r1/concepts/c1/v1.md",
  "bucket": "my-bucket",
  "size_bytes": 1024
}
```

**失败时：**
```json
{
  "event": "s3_download_failed",
  "key": "roadmaps/r1/concepts/c1/v1.md",
  "bucket": "my-bucket",
  "error": "NoSuchKey: The specified key does not exist."
}
```

## 配置

下载功能使用与上传相同的 S3 配置：

```python
# 在 .env 文件中配置
S3_ACCESS_KEY_ID=your_access_key
S3_SECRET_ACCESS_KEY=your_secret_key
S3_ENDPOINT_URL=https://your-endpoint.com
S3_REGION=auto
S3_BUCKET_NAME=your-bucket-name
```

## 注意事项

1. **编码限制**：当前仅支持 UTF-8 编码的文本文件。如需下载二进制文件，需要修改代码以支持 bytes 返回。

2. **内存限制**：大文件会完全加载到内存中。如果需要下载超大文件，建议使用流式下载。

3. **权限要求**：确保 S3 访问密钥具有 `s3:GetObject` 权限。

4. **异步操作**：所有方法都是异步的，必须在 async 上下文中调用。

## 相关文件

- 实现代码: `backend/app/tools/storage/s3_client.py`
- 域模型: `backend/app/models/domain.py` (S3DownloadRequest, S3DownloadResult)
- 配置: `backend/app/config/settings.py`

