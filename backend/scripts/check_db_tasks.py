#!/usr/bin/env python3
"""
检查数据库中的任务状态
"""
import asyncio
from sqlalchemy import select, desc
# CeleryRepositoryFactory 已删除，直接使用 get_celery_session
from app.models.database import RoadmapTask


async def main():
    """查询最近的任务"""
    
    async with repo_factory.create_session() as session:
        # 查询最近的 10 个任务
        result = await session.execute(
            select(RoadmapTask)
            .order_by(desc(RoadmapTask.created_at))
            .limit(10)
        )
        tasks = result.scalars().all()
        
        print("\n" + "=" * 120)
        print("数据库中最近的 10 个任务")
        print("=" * 120)
        
        for i, task in enumerate(tasks, 1):
            print(f"\n[{i}] Task ID: {task.task_id[:8]}...")
            print(f"    Status: {task.status:25} | Current Step: {task.current_step}")
            print(f"    Roadmap ID: {task.roadmap_id or 'N/A'}")
            print(f"    Created: {task.created_at} | Updated: {task.updated_at}")
            
            # 解析 user_request 获取学习目标
            if isinstance(task.user_request, dict):
                prefs = task.user_request.get('preferences', {})
                goal = prefs.get('learning_goal', 'N/A')
                print(f"    Goal: {goal}")
        
        print("\n" + "=" * 120)
        
        # 统计各状态的任务数
        print("\n📊 任务状态统计:")
        print("-" * 120)
        
        status_count = {}
        for task in tasks:
            status_count[task.status] = status_count.get(task.status, 0) + 1
        
        for status, count in sorted(status_count.items()):
            print(f"   {status:25} : {count} 个任务")


if __name__ == "__main__":
    asyncio.run(main())

