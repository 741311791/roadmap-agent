"""
修复僵尸状态（Stale Status）的脚本 - v2

适配新的数据库架构（RoadmapMetadata 和 RoadmapTask 独立）

运行方式：
    uv run python scripts/fix_stale_statuses_v2.py [--dry-run] [--roadmap-id ROADMAP_ID]

参数：
    --dry-run: 仅预览，不实际修改数据库
    --roadmap-id: 指定要检查的路线图 ID（可选，不指定则检查所有）
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
from app.models.database import RoadmapMetadata, RoadmapTask


async def find_and_fix_stale_statuses(
    session: AsyncSession,
    roadmap_id: str | None = None,
    dry_run: bool = True,
) -> dict:
    """
    查找并修复僵尸状态的概念
    
    Args:
        session: 数据库会话
        roadmap_id: 指定路线图 ID（可选）
        dry_run: 是否为预览模式
        
    Returns:
        修复结果统计
    """
    # 1. 获取所有活跃任务（按路线图分组）
    active_tasks_query = select(RoadmapTask).where(
        RoadmapTask.status.in_(["pending", "processing", "human_review_pending"])
    )
    result = await session.execute(active_tasks_query)
    active_tasks = result.scalars().all()
    
    # 按 roadmap_id 分组
    active_roadmaps = {}
    for task in active_tasks:
        if task.roadmap_id not in active_roadmaps:
            active_roadmaps[task.roadmap_id] = []
        active_roadmaps[task.roadmap_id].append(task)
    
    print(f"\n活跃任务统计:")
    print(f"  • 活跃任务总数: {len(active_tasks)}")
    print(f"  • 涉及路线图数: {len(active_roadmaps)}")
    
    for rid, tasks in active_roadmaps.items():
        print(f"    - {rid}: {len(tasks)} 个活跃任务")
        for task in tasks:
            status_info = f"{task.status}"
            if task.task_type == "retry":
                status_info += f" (重试: {task.content_type})"
            print(f"      • {task.task_id}: {status_info}")
    
    # 2. 获取要检查的路线图
    if roadmap_id:
        roadmap_query = select(RoadmapMetadata).where(
            RoadmapMetadata.roadmap_id == roadmap_id
        )
    else:
        roadmap_query = select(RoadmapMetadata).where(
            RoadmapMetadata.deleted_at.is_(None)  # 只检查未删除的路线图
        )
    
    result = await session.execute(roadmap_query)
    roadmaps = result.scalars().all()
    
    print(f"\n要检查的路线图: {len(roadmaps)} 个")
    
    # 3. 扫描僵尸状态
    stale_concepts = []
    
    for roadmap in roadmaps:
        # 检查该路线图是否有活跃任务
        has_active_task = roadmap.roadmap_id in active_roadmaps
        
        if has_active_task:
            # 有活跃任务，跳过（状态正常）
            continue
        
        framework_data = roadmap.framework_data
        
        for stage in framework_data.get("stages", []):
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    concept_id = concept.get("concept_id")
                    concept_name = concept.get("name")
                    
                    # 检查三种内容类型的状态
                    checks = [
                        ("tutorial", "content_status"),
                        ("resources", "resources_status"),
                        ("quiz", "quiz_status"),
                    ]
                    
                    for content_type, status_key in checks:
                        status = concept.get(status_key)
                        
                        # pending 或 generating 但没有活跃任务 → 僵尸状态
                        if status in ["pending", "generating"]:
                            stale_concepts.append({
                                "roadmap_id": roadmap.roadmap_id,
                                "roadmap_title": roadmap.title,
                                "concept_id": concept_id,
                                "concept_name": concept_name,
                                "content_type": content_type,
                                "current_status": status,
                                "status_key": status_key,
                            })
    
    print(f"\n检测到的僵尸状态: {len(stale_concepts)} 个")
    
    if not stale_concepts:
        return {
            "total_roadmaps": len(roadmaps),
            "stale_count": 0,
            "fixed_count": 0,
        }
    
    # 4. 显示详情
    print("\n僵尸状态详情:")
    print("=" * 80)
    
    by_roadmap = {}
    for item in stale_concepts:
        rid = item["roadmap_id"]
        if rid not in by_roadmap:
            by_roadmap[rid] = []
        by_roadmap[rid].append(item)
    
    for rid, items in by_roadmap.items():
        first = items[0]
        print(f"\n路线图: {first['roadmap_title']}")
        print(f"  ID: {rid}")
        print(f"  僵尸概念数: {len(items)}")
        
        for item in items:
            print(f"    • {item['concept_name']}")
            print(f"      内容类型: {item['content_type']}")
            print(f"      当前状态: {item['current_status']}")
    
    # 5. 修复（如果不是 dry-run）
    fixed_count = 0
    
    if not dry_run:
        print("\n开始修复...")
        print("=" * 80)
        
        for rid, items in by_roadmap.items():
            # 获取路线图
            result = await session.execute(
                select(RoadmapMetadata).where(RoadmapMetadata.roadmap_id == rid)
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
                            item for item in items
                            if item["concept_id"] == concept_id
                        ]
                        
                        for item in matching_items:
                            status_key = item["status_key"]
                            current_status = concept.get(status_key)
                            
                            if current_status in ["pending", "generating"]:
                                # 标记为 failed
                                concept[status_key] = "failed"
                                updated = True
                                fixed_count += 1
                                
                                print(f"  ✓ {item['concept_name']} ({item['content_type']}): {current_status} -> failed")
            
            if updated:
                roadmap.framework_data = framework_data
                session.add(roadmap)
        
        await session.commit()
        print(f"\n✅ 已修复 {fixed_count} 个概念的状态")
    else:
        print(f"\n⚠️  预览模式，未实际修改数据库")
        print(f"   如需修复，请运行: uv run python scripts/fix_stale_statuses_v2.py --no-dry-run")
    
    return {
        "total_roadmaps": len(roadmaps),
        "stale_count": len(stale_concepts),
        "fixed_count": fixed_count,
    }


async def main(roadmap_id: str | None = None, dry_run: bool = True):
    """主函数"""
    print("=" * 80)
    print("僵尸状态修复工具 v2")
    print("=" * 80)
    print(f"模式: {'预览模式（不会修改数据库）' if dry_run else '修复模式（将修改数据库）'}")
    if roadmap_id:
        print(f"路线图: {roadmap_id}")
    else:
        print("路线图: 全部")
    print()
    
    async with AsyncSessionLocal() as session:
        result = await find_and_fix_stale_statuses(
            session,
            roadmap_id=roadmap_id,
            dry_run=dry_run,
        )
        
        print("\n" + "=" * 80)
        print("完成")
        print("=" * 80)
        print(f"检查的路线图: {result['total_roadmaps']}")
        print(f"检测到的僵尸状态: {result['stale_count']}")
        print(f"已修复: {result['fixed_count']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="修复路线图中的僵尸状态")
    parser.add_argument(
        "--roadmap-id",
        type=str,
        default=None,
        help="指定要检查的路线图 ID（可选）",
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
    
    asyncio.run(main(roadmap_id=args.roadmap_id, dry_run=args.dry_run))

