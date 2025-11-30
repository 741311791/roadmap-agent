"""
MinIO 上传/下载功能测试脚本

测试功能：
1. 检查 MinIO 连接
2. 测试文件上传
3. 测试文件下载
4. 验证上传下载一致性

运行方式:
    cd backend
    uv run python scripts/test_minio.py
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


# 颜色代码
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{'=' * 60}")
    print(f"{text}")
    print(f"{'=' * 60}{Colors.END}\n")


def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")


def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")


def print_info(msg: str):
    print(f"{Colors.CYAN}ℹ️  {msg}{Colors.END}")


async def test_connection():
    """测试 MinIO 连接"""
    print_info("测试 MinIO 连接...")
    
    from app.db.minio_init import check_minio_connection
    from app.config.settings import settings
    
    print(f"   端点: {settings.S3_ENDPOINT_URL}")
    print(f"   Bucket: {settings.S3_BUCKET_NAME}")
    
    success = await check_minio_connection()
    
    if success:
        print_success("MinIO 连接成功")
        return True
    else:
        print_error("MinIO 连接失败，请检查配置")
        return False


async def test_bucket_init():
    """测试 Bucket 初始化"""
    print_info("测试 Bucket 初始化...")
    
    from app.db.minio_init import ensure_bucket_exists
    from app.config.settings import settings
    
    success = await ensure_bucket_exists()
    
    if success:
        print_success(f"Bucket '{settings.S3_BUCKET_NAME}' 已就绪")
        return True
    else:
        print_error("Bucket 初始化失败")
        return False


async def test_upload():
    """测试文件上传"""
    print_info("测试文件上传...")
    
    from app.tools.storage.s3_client import S3StorageTool
    from app.models.domain import S3UploadRequest
    
    # 创建测试内容
    test_content = f"""# MinIO 测试文件

这是一个自动生成的测试文件，用于验证 MinIO 上传功能。

## 测试信息

- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- 内容类型: text/markdown
- 测试目的: 验证上传功能

## 示例代码

```python
print("Hello, MinIO!")
```

---
测试完成！
"""
    
    test_key = f"test/minio_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    try:
        storage = S3StorageTool()
        
        request = S3UploadRequest(
            key=test_key,
            content=test_content,
            content_type="text/markdown",
        )
        
        result = await storage.execute(request)
        
        if result.success:
            print_success(f"上传成功!")
            print(f"   Key: {result.key}")
            print(f"   大小: {result.size_bytes} bytes")
            print(f"   ETag: {result.etag}")
            print(f"   URL: {result.url[:80]}...")
            return test_key, test_content
        else:
            print_error("上传失败")
            return None, None
            
    except Exception as e:
        print_error(f"上传异常: {e}")
        return None, None


async def test_download(key: str, expected_content: str):
    """测试文件下载"""
    print_info(f"测试文件下载: {key}")
    
    from app.tools.storage.s3_client import S3StorageTool
    from app.models.domain import S3DownloadRequest
    
    try:
        storage = S3StorageTool()
        
        request = S3DownloadRequest(key=key)
        result = await storage.download(request)
        
        if result.success:
            print_success("下载成功!")
            print(f"   Key: {result.key}")
            print(f"   大小: {result.size_bytes} bytes")
            print(f"   Content-Type: {result.content_type}")
            print(f"   ETag: {result.etag}")
            
            # 验证内容一致性
            if result.content == expected_content:
                print_success("内容验证通过 - 上传下载一致")
                return True
            else:
                print_error("内容验证失败 - 上传下载不一致")
                print(f"   预期长度: {len(expected_content)}")
                print(f"   实际长度: {len(result.content)}")
                return False
        else:
            print_error("下载失败")
            return False
            
    except Exception as e:
        print_error(f"下载异常: {e}")
        return False


async def test_download_nonexistent():
    """测试下载不存在的文件"""
    print_info("测试下载不存在的文件...")
    
    from app.tools.storage.s3_client import S3StorageTool
    from app.models.domain import S3DownloadRequest
    
    try:
        storage = S3StorageTool()
        
        request = S3DownloadRequest(key="nonexistent/file_that_does_not_exist.txt")
        result = await storage.download(request)
        
        # 应该抛出异常或返回失败
        print_error("应该抛出异常但没有")
        return False
        
    except Exception as e:
        print_success(f"正确抛出异常: {type(e).__name__}")
        return True


async def main():
    print_header("🧪 MinIO 上传/下载功能测试")
    
    results = {
        "connection": False,
        "bucket_init": False,
        "upload": False,
        "download": False,
        "content_verify": False,
        "error_handling": False,
    }
    
    # 1. 测试连接
    print(f"\n{Colors.BOLD}[1/5] 连接测试{Colors.END}")
    results["connection"] = await test_connection()
    
    if not results["connection"]:
        print_error("\n连接失败，跳过后续测试")
        return
    
    # 2. 测试 Bucket 初始化
    print(f"\n{Colors.BOLD}[2/5] Bucket 初始化测试{Colors.END}")
    results["bucket_init"] = await test_bucket_init()
    
    if not results["bucket_init"]:
        print_error("\nBucket 初始化失败，跳过后续测试")
        return
    
    # 3. 测试上传
    print(f"\n{Colors.BOLD}[3/5] 上传测试{Colors.END}")
    test_key, test_content = await test_upload()
    results["upload"] = test_key is not None
    
    if not results["upload"]:
        print_error("\n上传失败，跳过后续测试")
        return
    
    # 4. 测试下载
    print(f"\n{Colors.BOLD}[4/5] 下载测试{Colors.END}")
    results["download"] = await test_download(test_key, test_content)
    results["content_verify"] = results["download"]
    
    # 5. 测试错误处理
    print(f"\n{Colors.BOLD}[5/5] 错误处理测试{Colors.END}")
    results["error_handling"] = await test_download_nonexistent()
    
    # 打印测试结果汇总
    print_header("📊 测试结果汇总")
    
    all_passed = True
    for test_name, passed in results.items():
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if passed else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print_success("所有测试通过！MinIO 功能正常。")
    else:
        print_error("部分测试失败，请检查配置和 MinIO 服务状态。")


if __name__ == "__main__":
    asyncio.run(main())

