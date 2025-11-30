"""分析任务失败原因和教程生成情况"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.database import RoadmapTask
import structlog

logger = structlog.get_logger()


async def analyze_tasks():
    """分析任务状态和失败原因"""
    async with AsyncSessionLocal() as session:
        # 查询所有已完成的任务
        result_completed = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.status == "completed")
            .order_by(RoadmapTask.created_at.desc())
        )
        completed_tasks = result_completed.scalars().all()
        
        print(f"\n=== 已完成的任务: {len(completed_tasks)} 个 ===")
        for task in completed_tasks[:10]:
            print(f"Task ID: {task.task_id}")
            print(f"  Status: {task.status}")
            print(f"  Current Step: {task.current_step}")
            print(f"  Roadmap ID: {task.roadmap_id}")
            print(f"  Created: {task.created_at}")
            print()
        
        # 查询处于 human_review_pending 状态的任务
        result_pending = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.status == "human_review_pending")
            .order_by(RoadmapTask.created_at.desc())
        )
        pending_tasks = result_pending.scalars().all()
        
        print(f"\n=== 等待人工审核的任务: {len(pending_tasks)} 个 ===")
        for task in pending_tasks[:10]:
            print(f"Task ID: {task.task_id}")
            print(f"  Roadmap ID: {task.roadmap_id}")
            print(f"  Created: {task.created_at}")
            print()
        
        # 查询失败的任务
        result_failed = await session.execute(
            select(RoadmapTask)
            .where(RoadmapTask.status == "failed")
            .order_by(RoadmapTask.created_at.desc())
        )
        failed_tasks = result_failed.scalars().all()
        
        print(f"\n=== 失败的任务: {len(failed_tasks)} 个 ===")
        for task in failed_tasks[:10]:
            print(f"Task ID: {task.task_id}")
            print(f"  Current Step: {task.current_step}")
            print(f"  Error: {task.error_message[:200] if task.error_message else 'None'}")
            print(f"  Created: {task.created_at}")
            print()
        
        print("\n=== 分析结论 ===")
        print(f"1. 已完成任务数: {len(completed_tasks)}")
        print(f"2. 等待人工审核任务数: {len(pending_tasks)}")
        print(f"3. 失败任务数: {len(failed_tasks)}")
        print(f"\n提示: 如果有任务停留在 human_review_pending 状态，")
        print(f"     说明工作流在人工审核处被中断，教程生成未执行。")
        print(f"     需要批准任务后才会继续执行教程生成。")


if __name__ == "__main__":
    asyncio.run(analyze_tasks())

