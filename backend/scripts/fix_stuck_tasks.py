"""
修复卡住的任务

将运行时间超过阈值的任务标记为失败

运行方式：
    uv run python scripts/fix_stuck_tasks.py [--dry-run] [--timeout 300]

参数：
    --dry-run: 仅预览，不实际修改数据库
    --timeout: 超时阈值（秒），默认300秒（5分钟）
"""

import asyncio
import argparse
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import AsyncSessionLocal
from app.models.database import RoadmapTask, RoadmapMetadata


async def find_stuck_tasks(
    session: AsyncSession,
    timeout_seconds: int = 300,
) -> list[RoadmapTask]:
    """
    查找卡住的任务
    
    Args:
        session: 数据库会话
        timeout_seconds: 超时阈值（秒）
        
    Returns:
        卡住的任务列表
    """
    threshold = datetime.now() - timedelta(seconds=timeout_seconds)
    
    result = await session.execute(
        select(RoadmapTask).where(
            RoadmapTask.status.in_(["pending", "processing"]),
            RoadmapTask.created_at < threshold
        ).order_by(RoadmapTask.created_at)
    )
    
    return list(result.scalars().all())


async def fix_stuck_task(
    session: AsyncSession,
    task: RoadmapTask,
    dry_run: bool = True,
) -> bool:
    """
    修复单个卡住的任务
    
    Args:
        session: 数据库会话
        task: 任务对象
        dry_run: 是否为预览模式
        
    Returns:
        是否修复成功
    """
    # 更新任务状态为失败
    if not dry_run:
        task.status = "failed"
        task.error_message = "任务超时，已自动标记为失败"
        task.completed_at = datetime.now()
        session.add(task)
    
    # 如果是重试任务，需要更新路线图中对应概念的状态
    if task.task_type == "retry_resources" and task.concept_id:
        result = await session.execute(
            select(RoadmapMetadata).where(
                RoadmapMetadata.roadmap_id == task.roadmap_id
            )
        )
        roadmap = result.scalar_one_or_none()
        
        if roadmap:
            framework_data = roadmap.framework_data
            updated = False
            
            for stage in framework_data.get("stages", []):
                for module in stage.get("modules", []):
                    for concept in module.get("concepts", []):
                        if concept.get("concept_id") == task.concept_id:
                            # 更新资源状态为失败
                            if task.content_type == "resources":
                                concept["resources_status"] = "failed"
                            elif task.content_type == "tutorial":
                                concept["content_status"] = "failed"
                            elif task.content_type == "quiz":
                                concept["quiz_status"] = "failed"
                            
                            updated = True
                            break
                    if updated:
                        break
                if updated:
                    break
            
            if updated and not dry_run:
                roadmap.framework_data = framework_data
                session.add(roadmap)
    
    return True


async def main(timeout_seconds: int = 300, dry_run: bool = True):
    """主函数"""
    print("=" * 80)
    print("修复卡住的任务")
    print("=" * 80)
    print(f"模式: {'预览模式（不会修改数据库）' if dry_run else '修复模式（将修改数据库）'}")
    print(f"超时阈值: {timeout_seconds} 秒 ({timeout_seconds / 60:.1f} 分钟)")
    print()
    
    async with AsyncSessionLocal() as session:
        # 查找卡住的任务
        print("查找卡住的任务...")
        stuck_tasks = await find_stuck_tasks(session, timeout_seconds)
        
        if not stuck_tasks:
            print("✓ 未发现卡住的任务")
            return
        
        print(f"发现 {len(stuck_tasks)} 个卡住的任务:\n")
        
        # 显示详情
        now = datetime.now()
        for task in stuck_tasks:
            elapsed = now - task.created_at if task.created_at else None
            elapsed_str = str(elapsed).split('.')[0] if elapsed else "N/A"
            
            print(f"任务 ID: {task.task_id}")
            print(f"  类型: {task.task_type}")
            print(f"  状态: {task.status}")
            print(f"  当前步骤: {task.current_step}")
            print(f"  路线图: {task.roadmap_id}")
            if task.concept_id:
                print(f"  概念: {task.concept_id}")
                print(f"  内容类型: {task.content_type}")
            print(f"  创建时间: {task.created_at}")
            print(f"  运行时长: {elapsed_str}")
            print()
        
        if dry_run:
            print(f"⚠️  预览模式，未实际修改数据库")
            print(f"如需修复，请运行: uv run python scripts/fix_stuck_tasks.py --no-dry-run --timeout {timeout_seconds}")
        else:
            # 执行修复
            print("开始修复...")
            fixed_count = 0
            
            for task in stuck_tasks:
                try:
                    await fix_stuck_task(session, task, dry_run=False)
                    fixed_count += 1
                    print(f"✓ 已修复: {task.task_id}")
                except Exception as e:
                    print(f"✗ 修复失败: {task.task_id} - {str(e)}")
            
            await session.commit()
            print(f"\n✅ 已修复 {fixed_count}/{len(stuck_tasks)} 个任务")
    
    print("\n" + "=" * 80)
    print("完成")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="修复卡住的任务")
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="超时阈值（秒），默认300秒（5分钟）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="预览模式，不修改数据库（默认）",
    )
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        help="实际修复模式，会修改数据库",
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(timeout_seconds=args.timeout, dry_run=args.dry_run))

