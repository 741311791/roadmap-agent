#!/usr/bin/env python3
"""
检查用户任务数据

用于调试 GET /users/{user_id}/tasks 接口无法获取数据的问题
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.db.session import async_session_maker
from app.models.database import RoadmapTask
import structlog

logger = structlog.get_logger()


async def check_tasks():
    """检查数据库中的任务数据"""
    async with async_session_maker.begin() as session:
        # 1. 检查总任务数
        result = await session.execute(select(func.count()).select_from(RoadmapTask))
        total_count = result.scalar()
        print(f"\n📊 数据库中共有 {total_count} 个任务")
        
        if total_count == 0:
            print("❌ 数据库中没有任务记录！")
            return
        
        # 2. 按 user_id 分组统计
        result = await session.execute(
            select(RoadmapTask.user_id, func.count(RoadmapTask.task_id))
            .group_by(RoadmapTask.user_id)
        )
        user_stats = result.all()
        
        print(f"\n👥 按用户统计：")
        for user_id, count in user_stats:
            print(f"  - {user_id}: {count} 个任务")
        
        # 3. 检查 admin-001 用户的任务
        result = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.user_id == "admin-001")
            .order_by(RoadmapTask.created_at.desc())
            .limit(10)
        )
        admin_tasks = list(result.scalars().all())
        
        print(f"\n🔍 admin-001 用户的任务（最新10条）：")
        if not admin_tasks:
            print("  ❌ 没有找到 admin-001 的任务")
        else:
            for task in admin_tasks:
                title = "未知"
                if task.user_request:
                    learning_goal = task.user_request.get("preferences", {}).get("learning_goal", "")
                    if learning_goal:
                        title = learning_goal[:50]
                
                print(f"  - Task ID: {task.task_id}")
                print(f"    状态: {task.status}")
                print(f"    当前步骤: {task.current_step}")
                print(f"    标题: {title}")
                print(f"    Roadmap ID: {task.roadmap_id}")
                print(f"    创建时间: {task.created_at}")
                print()
        
        # 4. 检查最新的 5 个任务（不限用户）
        result = await session.execute(
            select(RoadmapTask)
            .order_by(RoadmapTask.created_at.desc())
            .limit(5)
        )
        recent_tasks = list(result.scalars().all())
        
        print(f"\n🕒 最新的 5 个任务（所有用户）：")
        for task in recent_tasks:
            print(f"  - Task ID: {task.task_id}")
            print(f"    User ID: {task.user_id}")
            print(f"    状态: {task.status}")
            print(f"    创建时间: {task.created_at}")
            print()


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 检查用户任务数据")
    print("=" * 60)
    
    asyncio.run(check_tasks())
    
    print("=" * 60)
    print("✅ 检查完成")
    print("=" * 60)













