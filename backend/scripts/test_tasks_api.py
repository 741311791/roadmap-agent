#!/usr/bin/env python3
"""
测试任务列表 API

直接测试 GET /api/v1/users/{user_id}/tasks 接口
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

async def test_api():
    """测试 API 端点"""
    base_url = "http://localhost:8000"
    user_id = "admin-001"
    
    # 测试任务列表接口
    url = f"{base_url}/api/v1/users/{user_id}/tasks"
    params = {"limit": 50, "offset": 0}
    
    print(f"\n📡 测试 API: {url}")
    print(f"   参数: {params}")
    print()
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            
            print(f"✅ 状态码: {response.status_code}")
            print(f"📄 响应头: {dict(response.headers)}")
            print()
            
            if response.status_code == 200:
                data = response.json()
                print(f"📊 响应数据:")
                print(f"   总数: {data.get('total', 0)}")
                print(f"   任务数: {len(data.get('tasks', []))}")
                print(f"   pending: {data.get('pending_count', 0)}")
                print(f"   processing: {data.get('processing_count', 0)}")
                print(f"   completed: {data.get('completed_count', 0)}")
                print(f"   failed: {data.get('failed_count', 0)}")
                print()
                
                if data.get('tasks'):
                    print("📋 前 3 个任务:")
                    for task in data['tasks'][:3]:
                        print(f"   - {task.get('task_id')}")
                        print(f"     状态: {task.get('status')}")
                        print(f"     标题: {task.get('title')}")
                        print()
            else:
                print(f"❌ 错误响应:")
                print(response.text)
    
    except httpx.ConnectError:
        print("❌ 无法连接到服务器（确保后端正在运行）")
    except Exception as e:
        print(f"❌ 错误: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 测试任务列表 API")
    print("=" * 60)
    
    asyncio.run(test_api())
    
    print("=" * 60)
    print("✅ 测试完成")
    print("=" * 60)






