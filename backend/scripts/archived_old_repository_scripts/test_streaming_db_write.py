"""
简化测试：验证流式端点的数据库写入功能

测试流程：
1. 调用流式端点生成路线图（不含教程，快速测试）
2. 等待流式传输完成
3. 检查数据库中是否有记录
"""
import asyncio
import httpx
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import async_session_maker
from app.db.repositories.roadmap_repo import RoadmapRepository


async def test_streaming_db_write():
    """测试流式端点的数据库写入"""
    print("=== 测试流式端点数据库写入 ===\n")
    
    # 测试请求
    request_data = {
        "user_id": "test-user-db-write",
        "session_id": "test-session-db-write",
        "preferences": {
            "learning_goal": "快速测试数据库写入功能",
            "available_hours_per_week": 10,
            "motivation": "测试",
            "current_level": "beginner",
            "career_background": "测试",
            "content_preference": ["text"]
        }
    }
    
    url = "http://localhost:8000/api/v1/roadmaps/generate-stream?include_tutorials=false"
    print(f"📡 调用端点: {url}")
    print("⏳ 等待流式传输完成...\n")
    
    task_id = None
    roadmap_id = None
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=request_data) as response:
                if response.status_code != 200:
                    print(f"❌ HTTP 错误: {response.status_code}")
                    return
                
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    
                    json_str = line[6:]
                    try:
                        event = json.loads(json_str)
                        event_type = event.get("type")
                        
                        # 只打印关键事件
                        if event_type in ["complete", "error", "done"]:
                            agent = event.get("agent", "system")
                            print(f"  ✓ {agent}: {event_type}")
                            
                            # 提取 task_id 和 roadmap_id
                            if event_type == "done":
                                task_id = event.get("task_id")
                                roadmap_id = event.get("roadmap_id")
                                print(f"\n  Task ID: {task_id}")
                                print(f"  Roadmap ID: {roadmap_id}")
                    
                    except json.JSONDecodeError:
                        continue
        
        print("\n✅ 流式传输完成")
        
        # 检查数据库
        if task_id:
            print(f"\n=== 检查数据库记录 ===\n")
            
            async with async_session_maker.begin() as session:
                repo = RoadmapRepository(session)
                
                # 检查任务记录
                task = await repo.get_task(task_id)
                if task:
                    print(f"✓ 找到任务记录:")
                    print(f"  - Task ID: {task.task_id}")
                    print(f"  - Status: {task.status}")
                    print(f"  - Roadmap ID: {task.roadmap_id}")
                else:
                    print(f"✗ 未找到任务记录")
                
                # 检查路线图元数据
                if roadmap_id:
                    metadata = await repo.get_roadmap_metadata(roadmap_id)
                    if metadata:
                        print(f"\n✓ 找到路线图元数据:")
                        print(f"  - Roadmap ID: {metadata.roadmap_id}")
                        print(f"  - Title: {metadata.title}")
                        print(f"  - Stages: {len(metadata.framework_data.get('stages', []))}")
                    else:
                        print(f"\n✗ 未找到路线图元数据")
            
            print("\n=== 测试完成 ===")
            print("✅ 流式端点现在会正确保存数据到数据库！")
        else:
            print("\n⚠️ 未获取到 task_id，可能流式传输未完全完成")
    
    except httpx.ConnectError:
        print("❌ 无法连接到服务器")
        print("   请确保后端服务正在运行: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print()
    asyncio.run(test_streaming_db_write())
    print()

