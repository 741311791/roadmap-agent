#!/usr/bin/env python3
"""
修复任务的 user_id

将数据库中的测试任务关联到实际登录的用户
"""
import asyncio
from sqlalchemy import select, update
from app.db.session import async_session_maker
from app.models.database import RoadmapTask

OLD_USER_ID = "e2e-test-permanent-user-id-00000001"
NEW_USER_ID = "6a01178a-5d0a-4729-9a09-f32520731e23"  # 实际登录用户的 ID


async def fix_task_user_ids():
    """修复任务的 user_id"""
    async with async_session_maker() as session:
        # 查询所有旧 user_id 的任务
        stmt = select(RoadmapTask).where(RoadmapTask.user_id == OLD_USER_ID)
        result = await session.execute(stmt)
        tasks = result.scalars().all()
        
        if not tasks:
            print(f"❌ 未找到 user_id 为 {OLD_USER_ID} 的任务")
            return
        
        print(f"找到 {len(tasks)} 个任务需要更新：")
        for task in tasks:
            print(f"  - {task.task_id} ({task.status})")
        
        # 更新 user_id
        stmt = (
            update(RoadmapTask)
            .where(RoadmapTask.user_id == OLD_USER_ID)
            .values(user_id=NEW_USER_ID)
        )
        await session.execute(stmt)
        await session.commit()
        
        print(f"\n✅ 已将 {len(tasks)} 个任务的 user_id 从 {OLD_USER_ID} 更新为 {NEW_USER_ID}")


if __name__ == "__main__":
    asyncio.run(fix_task_user_ids())
