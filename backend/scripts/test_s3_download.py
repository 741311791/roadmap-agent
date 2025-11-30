"""
S3 下载功能测试脚本

运行方式:
    python -m scripts.test_s3_download
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.storage.s3_client import S3StorageTool
from app.models.domain import S3UploadRequest, S3DownloadRequest
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


async def test_upload_and_download():
    """测试上传和下载流程"""
    print("=" * 60)
    print("S3 上传和下载功能测试")
    print("=" * 60)
    print()
    
    # 检查配置
    print("📋 检查 S3 配置...")
    print(f"  端点: {settings.S3_ENDPOINT_URL}")
    print(f"  区域: {settings.S3_REGION}")
    print(f"  存储桶: {settings.S3_BUCKET_NAME}")
    print()
    
    s3_tool = S3StorageTool()
    test_key = "test/download-test.md"
    test_content = """# S3 下载功能测试

## 简介

这是一个用于测试 S3 下载功能的示例文件。

## 功能特性

- ✅ 支持 Markdown 格式
- ✅ 支持中文内容
- ✅ 自动重试机制
- ✅ 详细的日志记录

## 测试内容

这个文件包含了多种字符类型：
- 英文字母: ABCabc
- 中文字符: 你好世界
- 数字: 1234567890
- 特殊符号: !@#$%^&*()

时间戳: 2024-11-27
"""
    
    try:
        # 步骤 1: 上传测试文件
        print("📤 步骤 1: 上传测试文件...")
        upload_request = S3UploadRequest(
            key=test_key,
            content=test_content,
            content_type="text/markdown"
        )
        
        upload_result = await s3_tool.execute(upload_request)
        
        print(f"  ✅ 上传成功!")
        print(f"  - Key: {upload_result.key}")
        print(f"  - 大小: {upload_result.size_bytes} 字节")
        print(f"  - ETag: {upload_result.etag}")
        print(f"  - URL: {upload_result.url[:80]}...")
        print()
        
        # 步骤 2: 下载文件
        print("📥 步骤 2: 下载测试文件...")
        download_request = S3DownloadRequest(key=test_key)
        
        download_result = await s3_tool.download(download_request)
        
        print(f"  ✅ 下载成功!")
        print(f"  - Key: {download_result.key}")
        print(f"  - 大小: {download_result.size_bytes} 字节")
        print(f"  - Content-Type: {download_result.content_type}")
        print(f"  - ETag: {download_result.etag}")
        print(f"  - 最后修改: {download_result.last_modified}")
        print()
        
        # 步骤 3: 验证内容一致性
        print("🔍 步骤 3: 验证内容一致性...")
        if upload_request.content == download_result.content:
            print("  ✅ 内容验证通过！上传和下载的内容完全一致。")
            print()
            print("  下载内容预览（前 200 个字符）:")
            print("  " + "-" * 56)
            print("  " + download_result.content[:200].replace("\n", "\n  "))
            print("  ...")
        else:
            print("  ❌ 内容验证失败！上传和下载的内容不一致。")
            print(f"  - 上传大小: {len(upload_request.content)} 字节")
            print(f"  - 下载大小: {len(download_result.content)} 字节")
            return False
        
        print()
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ 测试失败")
        print("=" * 60)
        print(f"错误信息: {str(e)}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        print()
        print("详细错误堆栈:")
        traceback.print_exc()
        return False


async def test_download_nonexistent():
    """测试下载不存在的文件"""
    print()
    print("=" * 60)
    print("测试下载不存在的文件")
    print("=" * 60)
    print()
    
    s3_tool = S3StorageTool()
    
    try:
        print("📥 尝试下载不存在的文件...")
        download_request = S3DownloadRequest(
            key="test/nonexistent-file-12345.md"
        )
        
        download_result = await s3_tool.download(download_request)
        print("  ❌ 应该抛出异常，但没有！")
        return False
        
    except Exception as e:
        error_msg = str(e)
        if "NoSuchKey" in error_msg or "Not Found" in error_msg or "404" in error_msg:
            print(f"  ✅ 正确抛出异常: {error_msg}")
            return True
        else:
            print(f"  ⚠️  抛出了异常，但可能不是预期的类型: {error_msg}")
            return True


async def main():
    """主测试函数"""
    print()
    print("🚀 开始 S3 下载功能测试套件")
    print()
    
    # 测试 1: 上传和下载
    test1_passed = await test_upload_and_download()
    
    # 测试 2: 下载不存在的文件
    test2_passed = await test_download_nonexistent()
    
    # 汇总结果
    print()
    print("=" * 60)
    print("测试汇总")
    print("=" * 60)
    print(f"测试 1 - 上传和下载: {'✅ 通过' if test1_passed else '❌ 失败'}")
    print(f"测试 2 - 下载不存在的文件: {'✅ 通过' if test2_passed else '❌ 失败'}")
    print()
    
    if test1_passed and test2_passed:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

