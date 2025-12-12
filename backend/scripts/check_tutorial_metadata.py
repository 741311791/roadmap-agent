"""检查 tutorial_metadata 表数据"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.database import TutorialMetadata, RoadmapMetadata, RoadmapTask
import structlog

logger = structlog.get_logger()


async def check_tables():
    """检查数据库表中的数据"""
    async with AsyncSessionLocal() as session:
        # 查询 tutorial_metadata 表
        result_tutorials = await session.execute(
            select(func.count()).select_from(TutorialMetadata)
        )
        tutorial_count = result_tutorials.scalar()
        
        # 查询 roadmap_metadata 表
        result_roadmaps = await session.execute(
            select(func.count()).select_from(RoadmapMetadata)
        )
        roadmap_count = result_roadmaps.scalar()
        
        # 查询 roadmap_tasks 表
        result_tasks = await session.execute(
            select(func.count()).select_from(RoadmapTask)
        )
        task_count = result_tasks.scalar()
        
        print("\n=== 数据库表统计 ===")
        print(f"tutorial_metadata: {tutorial_count} 条记录")
        print(f"roadmap_metadata: {roadmap_count} 条记录")
        print(f"roadmap_tasks: {task_count} 条记录")
        
        # 查询最近的几个任务
        result_recent_tasks = await session.execute(
            select(RoadmapTask)
            .order_by(RoadmapTask.created_at.desc())
            .limit(5)
        )
        recent_tasks = result_recent_tasks.scalars().all()
        
        print("\n=== 最近的任务 ===")
        for task in recent_tasks:
            print(f"Task ID: {task.task_id}")
            print(f"  Status: {task.status}")
            print(f"  Current Step: {task.current_step}")
            print(f"  Roadmap ID: {task.roadmap_id}")
            print(f"  Created: {task.created_at}")
            print(f"  Error: {task.error_message if task.error_message else 'None'}")
            print()
        
        # 如果有roadmap，查询对应的tutorial_metadata
        if roadmap_count > 0:
            result_roadmaps_list = await session.execute(
                select(RoadmapMetadata)
                .order_by(RoadmapMetadata.created_at.desc())
                .limit(3)
            )
            roadmaps = result_roadmaps_list.scalars().all()
            
            print("\n=== 最近的路线图 ===")
            for roadmap in roadmaps:
                print(f"Roadmap ID: {roadmap.roadmap_id}")
                print(f"  Title: {roadmap.title}")
                
                # 查询对应的任务
                result_task = await session.execute(
                    select(RoadmapTask)
                    .where(RoadmapTask.roadmap_id == roadmap.roadmap_id)
                    .order_by(RoadmapTask.created_at.desc())
                    .limit(1)
                )
                task = result_task.scalar_one_or_none()
                print(f"  Task ID: {task.task_id if task else 'N/A'}")
                
                # 查询该路线图的教程
                result_tutorials_for_roadmap = await session.execute(
                    select(TutorialMetadata)
                    .where(TutorialMetadata.roadmap_id == roadmap.roadmap_id)
                )
                tutorials = result_tutorials_for_roadmap.scalars().all()
                print(f"  Tutorials: {len(tutorials)} 个")
                
                for tutorial in tutorials[:3]:  # 只显示前3个
                    print(f"    - {tutorial.title} (concept_id: {tutorial.concept_id})")
                print()


if __name__ == "__main__":
    asyncio.run(check_tables())

