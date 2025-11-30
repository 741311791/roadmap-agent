"""检查教程文件内容"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.minio_init import _get_minio_client


async def check_tutorial_content():
    """检查教程文件的实际内容"""
    client = _get_minio_client()
    bucket = "roadmap"
    
    # 检查几个教程文件
    keys = [
        "roadmaps/python-print-basics-2024/concepts/c-1-1-1/v1.md",
        "roadmaps/python-print-basics-2024/concepts/c-1-1-2/v1.md",
        "roadmaps/python-print-basics-2024/concepts/c-1-2-1/v1.md",
    ]
    
    for key in keys:
        try:
            # 下载文件
            response = await asyncio.to_thread(
                client.get_object,
                bucket,
                key
            )
            content = response.read().decode('utf-8')
            
            print(f"\n{'='*60}")
            print(f"文件: {key}")
            print(f"大小: {len(content)} 字节")
            print(f"{'='*60}")
            
            if len(content) == 0:
                print("⚠️ 文件为空！")
            else:
                print(f"内容预览（前500字符）:\n{content[:500]}")
                
        except Exception as e:
            print(f"\n✗ 读取 {key} 失败: {str(e)}")


if __name__ == "__main__":
    asyncio.run(check_tutorial_content())

