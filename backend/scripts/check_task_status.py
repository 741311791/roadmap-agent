"""
检查特定任务的详细状态

运行方式：
    uv run python scripts/check_task_status.py --task-id TASK_ID
"""

import asyncio
import argparse
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import AsyncSessionLocal
from app.models.database import RoadmapTask


async def check_task(task_id: str):
    """检查任务状态"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RoadmapTask).where(RoadmapTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            print(f"❌ 任务不存在: {task_id}")
            return
        
        print("=" * 80)
        print("任务详细信息")
        print("=" * 80)
        print(f"任务 ID: {task.task_id}")
        print(f"用户 ID: {task.user_id}")
        print(f"路线图 ID: {task.roadmap_id}")
        print(f"任务类型: {task.task_type}")
        print(f"状态: {task.status}")
        print(f"当前步骤: {task.current_step}")
        print(f"概念 ID: {task.concept_id}")
        print(f"内容类型: {task.content_type}")
        print(f"创建时间: {task.created_at}")
        print(f"更新时间: {task.updated_at}")
        print(f"完成时间: {task.completed_at}")
        
        # 计算运行时长
        now = datetime.now()
        if task.created_at:
            elapsed = now - task.created_at
            print(f"运行时长: {elapsed}")
            
            if task.status in ["processing", "pending"] and elapsed.total_seconds() > 300:
                print(f"\n⚠️  警告: 任务运行超过5分钟，可能已卡住")
        
        if task.error_message:
            print(f"\n错误信息: {task.error_message}")
        
        if task.user_request:
            print(f"\n用户请求:")
            import json
            print(json.dumps(task.user_request, indent=2, ensure_ascii=False))


async def list_processing_tasks():
    """列出所有正在运行的任务"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(RoadmapTask).where(
                RoadmapTask.status.in_(["pending", "processing", "human_review_pending"])
            ).order_by(RoadmapTask.created_at.desc())
        )
        tasks = result.scalars().all()
        
        print("=" * 80)
        print(f"所有正在运行的任务 (共 {len(tasks)} 个)")
        print("=" * 80)
        
        now = datetime.now()
        for task in tasks:
            elapsed = now - task.created_at if task.created_at else None
            elapsed_str = str(elapsed).split('.')[0] if elapsed else "N/A"
            
            info = f"{task.task_id} | {task.status} | {task.task_type}"
            if task.concept_id:
                info += f" | {task.content_type}"
            info += f" | 运行时长: {elapsed_str}"
            
            print(info)
            
            if elapsed and elapsed.total_seconds() > 300:
                print("  ⚠️  警告: 运行超过5分钟")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="检查任务状态")
    parser.add_argument(
        "--task-id",
        type=str,
        default=None,
        help="要检查的任务 ID",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出所有正在运行的任务",
    )
    
    args = parser.parse_args()
    
    if args.list:
        asyncio.run(list_processing_tasks())
    elif args.task_id:
        asyncio.run(check_task(args.task_id))
    else:
        print("请指定 --task-id 或 --list")

