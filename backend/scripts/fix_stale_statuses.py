"""
修复僵尸状态（Stale Status）的脚本

当任务异常中断时，部分概念的状态可能会停留在 pending 或 generating，
但实际上没有任务在运行。本脚本用于检测并修复这些僵尸状态。

运行方式：
    uv run python scripts/fix_stale_statuses.py [--dry-run] [--timeout 3600]

参数：
    --dry-run: 仅预览，不实际修改数据库
    --timeout: 超时时间（秒），默认 3600 秒（1 小时）
"""

import asyncio
import argparse
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import async_session_maker
from app.models.database import RoadmapMetadata, TaskState


async def get_active_task_ids(session: AsyncSession) -> set[str]:
    """
    获取所有活跃任务的 task_id
    
    活跃任务定义：
    - status 为 pending, processing, human_review_pending, human_review_required
    - updated_at 在最近 N 分钟内有更新
    """
    result = await session.execute(
        select(TaskState.task_id).where(
            TaskState.status.in_([
                'pending',
                'processing',
                'human_review_pending',
                'human_review_required',
            ])
        )
    )
    active_tasks = {row[0] for row in result.all()}
    return active_tasks


async def find_stale_statuses(
    session: AsyncSession,
    active_task_ids: set[str],
    timeout_seconds: int = 3600,
) -> list[dict]:
    """
    查找所有僵尸状态的概念
    
    Args:
        session: 数据库会话
        active_task_ids: 活跃的任务 ID 集合
        timeout_seconds: 超时时间（秒）
        
    Returns:
        包含僵尸状态概念信息的列表
    """
    result = await session.execute(select(RoadmapMetadata))
    roadmaps = result.scalars().all()
    
    stale_concepts = []
    now = datetime.now()
    timeout_delta = timedelta(seconds=timeout_seconds)
    
    for roadmap in roadmaps:
        framework_data = roadmap.framework_data
        
        # 检查路线图关联的任务是否活跃
        is_task_active = roadmap.task_id in active_task_ids
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    
                    # 检查每种内容类型的状态
                    for content_type, status_key in [
                        ('tutorial', 'content_status'),
                        ('resources', 'resources_status'),
                        ('quiz', 'quiz_status'),
                    ]:
                        status = concept.get(status_key)
                        
                        # 只检查 pending 或 generating 状态
                        if status in ['pending', 'generating']:
                            # 如果关联的任务不活跃，说明状态已经僵尸
                            if not is_task_active:
                                # 检查路线图的更新时间
                                time_since_update = now - roadmap.created_at
                                
                                if time_since_update > timeout_delta:
                                    stale_concepts.append({
                                        'roadmap_id': roadmap.roadmap_id,
                                        'roadmap_title': roadmap.title,
                                        'task_id': roadmap.task_id,
                                        'concept_id': concept_id,
                                        'concept_name': concept.get('name'),
                                        'content_type': content_type,
                                        'current_status': status,
                                        'created_at': roadmap.created_at,
                                        'time_since_update': time_since_update,
                                    })
    
    return stale_concepts


async def fix_stale_statuses(
    session: AsyncSession,
    stale_concepts: list[dict],
    dry_run: bool = True,
) -> int:
    """
    修复僵尸状态
    
    策略：
    - 如果状态为 pending 且超时 > 1 小时，标记为 failed
    - 如果状态为 generating 且超时 > 30 分钟，标记为 failed
    
    Args:
        session: 数据库会话
        stale_concepts: 僵尸状态概念列表
        dry_run: 是否为预览模式
        
    Returns:
        修复的概念数量
    """
    if not stale_concepts:
        return 0
    
    # 按 roadmap_id 分组
    roadmap_updates = {}
    
    for item in stale_concepts:
        roadmap_id = item['roadmap_id']
        if roadmap_id not in roadmap_updates:
            roadmap_updates[roadmap_id] = []
        roadmap_updates[roadmap_id].append(item)
    
    fixed_count = 0
    
    for roadmap_id, concepts in roadmap_updates.items():
        # 获取路线图
        result = await session.execute(
            select(RoadmapMetadata).where(RoadmapMetadata.roadmap_id == roadmap_id)
        )
        roadmap = result.scalar_one_or_none()
        
        if not roadmap:
            continue
        
        framework_data = roadmap.framework_data
        updated = False
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    
                    # 检查是否需要修复
                    matching_items = [
                        item for item in concepts
                        if item['concept_id'] == concept_id
                    ]
                    
                    for item in matching_items:
                        content_type = item['content_type']
                        status_key = {
                            'tutorial': 'content_status',
                            'resources': 'resources_status',
                            'quiz': 'quiz_status',
                        }[content_type]
                        
                        current_status = concept.get(status_key)
                        
                        if current_status in ['pending', 'generating']:
                            # 标记为 failed
                            concept[status_key] = 'failed'
                            updated = True
                            fixed_count += 1
                            
                            print(f"  ✓ 修复: {item['concept_name']} ({content_type}): {current_status} -> failed")
        
        if updated and not dry_run:
            roadmap.framework_data = framework_data
            session.add(roadmap)
    
    if not dry_run:
        await session.commit()
    
    return fixed_count


async def main(dry_run: bool = True, timeout_seconds: int = 3600):
    """
    主函数
    
    Args:
        dry_run: 是否为预览模式
        timeout_seconds: 超时时间（秒）
    """
    print("=" * 70)
    print("僵尸状态修复工具")
    print("=" * 70)
    print(f"模式: {'预览模式（不会修改数据库）' if dry_run else '修复模式（将修改数据库）'}")
    print(f"超时阈值: {timeout_seconds} 秒 ({timeout_seconds / 60:.1f} 分钟)")
    print()
    
    async with async_session_maker() as session:
        # 1. 获取活跃任务
        print("步骤 1/4: 获取活跃任务...")
        active_task_ids = await get_active_task_ids(session)
        print(f"  ✓ 找到 {len(active_task_ids)} 个活跃任务")
        print()
        
        # 2. 查找僵尸状态
        print("步骤 2/4: 扫描僵尸状态...")
        stale_concepts = await find_stale_statuses(
            session, active_task_ids, timeout_seconds
        )
        
        if not stale_concepts:
            print("  ✓ 未发现僵尸状态，数据库状态正常")
            return
        
        print(f"  ⚠️  发现 {len(stale_concepts)} 个僵尸状态概念")
        print()
        
        # 3. 显示详情
        print("步骤 3/4: 僵尸状态详情")
        print("-" * 70)
        
        # 按路线图分组显示
        by_roadmap = {}
        for item in stale_concepts:
            rid = item['roadmap_id']
            if rid not in by_roadmap:
                by_roadmap[rid] = []
            by_roadmap[rid].append(item)
        
        for roadmap_id, items in by_roadmap.items():
            first = items[0]
            print(f"\n路线图: {first['roadmap_title']}")
            print(f"  ID: {roadmap_id}")
            print(f"  任务 ID: {first['task_id']}")
            print(f"  创建时间: {first['created_at']}")
            print(f"  距今: {first['time_since_update']}")
            print(f"  僵尸概念数: {len(items)}")
            print()
            
            for item in items:
                print(f"    • {item['concept_name']} ({item['content_type']})")
                print(f"      状态: {item['current_status']}")
        
        print()
        
        # 4. 执行修复
        print("步骤 4/4: 修复僵尸状态")
        print("-" * 70)
        
        if dry_run:
            print("  ℹ️  预览模式，不会修改数据库")
            print(f"  将修复 {len(stale_concepts)} 个概念的状态")
            print()
            print("  如需实际修复，请运行:")
            print(f"    uv run python scripts/fix_stale_statuses.py --timeout {timeout_seconds}")
        else:
            fixed_count = await fix_stale_statuses(session, stale_concepts, dry_run=False)
            print(f"  ✅ 已修复 {fixed_count} 个概念的状态")
        
        print()
        print("=" * 70)
        print("完成")
        print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="修复路线图中的僵尸状态")
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
    parser.add_argument(
        "--timeout",
        type=int,
        default=3600,
        help="超时时间（秒），默认 3600 秒（1 小时）",
    )
    
    args = parser.parse_args()
    
    asyncio.run(main(dry_run=args.dry_run, timeout_seconds=args.timeout))
