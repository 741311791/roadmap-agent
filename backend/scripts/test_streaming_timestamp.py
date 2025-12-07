"""
带时间戳的流式测试：验证是否真的写入了新数据

1. 记录测试开始时间
2. 运行流式端点
3. 检查是否有新的数据库记录
"""
import asyncio
import httpx
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.database import RoadmapTask, RoadmapMetadata, TutorialMetadata


async def test_with_timestamp():
    """带时间戳的测试"""
    print("\n" + "="*70)
    print("流式端点数据库写入测试（带时间戳）")
    print("="*70 + "\n")
    
    # 记录测试开始时间
    test_start_time = datetime.now()
    print(f"📅 测试开始时间: {test_start_time}")
    
    # 检查测试前的数据库状态
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RoadmapTask).where(RoadmapTask.created_at >= test_start_time)
        )
        tasks_before = result.scalars().all()
        
        result = await session.execute(
            select(RoadmapMetadata).where(RoadmapMetadata.created_at >= test_start_time)
        )
        roadmaps_before = result.scalars().all()
        
        print(f"测试前（{test_start_time}之后）:")
        print(f"  - Tasks: {len(tasks_before)}")
        print(f"  - Roadmaps: {len(roadmaps_before)}")
    
    print("\n" + "-"*70)
    print("开始调用流式端点...")
    print("-"*70 + "\n")
    
    # 测试请求
    request_data = {
        "user_id": f"test-streaming-{test_start_time.strftime('%H%M%S')}",
        "session_id": f"session-{test_start_time.strftime('%H%M%S')}",
        "preferences": {
            "learning_goal": f"测试流式端点数据库写入 - {test_start_time.strftime('%H:%M:%S')}",
            "available_hours_per_week": 5,
            "motivation": "测试",
            "current_level": "beginner",
            "career_background": "测试工程师",
            "content_preference": ["text"]
        }
    }
    
    # 使用不含教程的版本（更快）
    url = "http://localhost:8000/api/v1/roadmaps/generate-stream?include_tutorials=false"
    
    task_id_from_stream = None
    roadmap_id_from_stream = None
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=request_data) as response:
                if response.status_code != 200:
                    print(f"❌ HTTP 错误: {response.status_code}")
                    return
                
                print("✓ 开始接收流式数据...\n")
                
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    
                    json_str = line[6:]
                    try:
                        event = json.loads(json_str)
                        event_type = event.get("type")
                        
                        # 打印关键事件
                        if event_type == "complete":
                            agent = event.get("agent", "")
                            print(f"  ✓ {agent} 完成")
                        elif event_type == "done":
                            task_id_from_stream = event.get("task_id")
                            roadmap_id_from_stream = event.get("roadmap_id")
                            print(f"\n✓ 流式传输完成")
                            print(f"  Task ID: {task_id_from_stream}")
                            print(f"  Roadmap ID: {roadmap_id_from_stream}")
                    
                    except json.JSONDecodeError:
                        continue
        
        test_end_time = datetime.now()
        elapsed = (test_end_time - test_start_time).total_seconds()
        
        print(f"\n📅 测试结束时间: {test_end_time}")
        print(f"⏱️  耗时: {elapsed:.1f} 秒")
        
        # 检查数据库
        print("\n" + "-"*70)
        print("检查数据库写入...")
        print("-"*70 + "\n")
        
        async with AsyncSessionLocal() as session:
            # 检查测试后的新记录
            result = await session.execute(
                select(RoadmapTask).where(RoadmapTask.created_at >= test_start_time)
            )
            tasks_after = result.scalars().all()
            
            result = await session.execute(
                select(RoadmapMetadata).where(RoadmapMetadata.created_at >= test_start_time)
            )
            roadmaps_after = result.scalars().all()
            
            result = await session.execute(
                select(TutorialMetadata).where(TutorialMetadata.generated_at >= test_start_time)
            )
            tutorials_after = result.scalars().all()
            
            print(f"测试后（{test_start_time}之后）:")
            print(f"  - Tasks: {len(tasks_after)} (新增: {len(tasks_after) - len(tasks_before)})")
            print(f"  - Roadmaps: {len(roadmaps_after)} (新增: {len(roadmaps_after) - len(roadmaps_before)})")
            print(f"  - Tutorials: {len(tutorials_after)}")
            
            # 详细检查
            if len(tasks_after) > len(tasks_before):
                print("\n✅ 发现新的任务记录:")
                for task in tasks_after:
                    if task not in tasks_before:
                        print(f"  • Task ID: {task.task_id}")
                        print(f"    User: {task.user_id}")
                        print(f"    Status: {task.status}")
                        print(f"    Roadmap: {task.roadmap_id}")
                        print(f"    Created: {task.created_at}")
            else:
                print("\n⚠️  没有新的任务记录！")
            
            if len(roadmaps_after) > len(roadmaps_before):
                print("\n✅ 发现新的路线图记录:")
                for rm in roadmaps_after:
                    if rm not in roadmaps_before:
                        print(f"  • Roadmap ID: {rm.roadmap_id}")
                        print(f"    Title: {rm.title}")
                        print(f"    Task: {rm.task_id}")
                        print(f"    Created: {rm.created_at}")
            else:
                print("\n⚠️  没有新的路线图记录！")
            
            # 检查流式返回的 task_id
            if task_id_from_stream:
                print(f"\n检查流式返回的 task_id: {task_id_from_stream}")
                result = await session.execute(
                    select(RoadmapTask).where(RoadmapTask.task_id == task_id_from_stream)
                )
                specific_task = result.scalar_one_or_none()
                
                if specific_task:
                    print(f"✅ 找到对应的任务记录")
                else:
                    print(f"❌ 未找到对应的任务记录！")
            
            # 检查流式返回的 roadmap_id
            if roadmap_id_from_stream:
                print(f"\n检查流式返回的 roadmap_id: {roadmap_id_from_stream}")
                result = await session.execute(
                    select(RoadmapMetadata).where(RoadmapMetadata.roadmap_id == roadmap_id_from_stream)
                )
                specific_roadmap = result.scalar_one_or_none()
                
                if specific_roadmap:
                    print(f"✅ 找到对应的路线图记录")
                else:
                    print(f"❌ 未找到对应的路线图记录！")
        
        print("\n" + "="*70)
        print("测试完成")
        print("="*70 + "\n")
    
    except httpx.ConnectError:
        print("❌ 无法连接到服务器")
        print("   请确保后端服务正在运行")
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_with_timestamp())














