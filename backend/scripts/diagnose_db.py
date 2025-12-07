"""
详细诊断脚本：检查流式端点的数据库写入情况

逐步检查：
1. checkpoint 数据
2. roadmap_tasks 表
3. roadmap_metadata 表
4. tutorial_metadata 表
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text, func
from app.db.session import AsyncSessionLocal
from app.models.database import RoadmapTask, RoadmapMetadata, TutorialMetadata
from app.core.orchestrator import RoadmapOrchestrator
import structlog

logger = structlog.get_logger()


async def diagnose_database():
    """诊断数据库各表的写入情况"""
    print("\n" + "="*70)
    print("数据库写入诊断工具")
    print("="*70 + "\n")
    
    async with AsyncSessionLocal() as session:
        # 1. 检查 checkpoint 表（LangGraph）
        print("1️⃣  检查 LangGraph Checkpoint 表")
        print("-" * 70)
        try:
            # 检查是否有 checkpoint 表
            result = await session.execute(
                text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE 'checkpoint%'
                """)
            )
            checkpoint_tables = result.fetchall()
            
            if checkpoint_tables:
                print(f"✓ 找到 {len(checkpoint_tables)} 个 checkpoint 表:")
                for table in checkpoint_tables:
                    print(f"  - {table[0]}")
                    
                    # 检查每个表的记录数
                    count_result = await session.execute(
                        text(f"SELECT COUNT(*) FROM {table[0]}")
                    )
                    count = count_result.scalar()
                    print(f"    记录数: {count}")
            else:
                print("⚠️  未找到 checkpoint 表（这是正常的，如果使用流式端点）")
        except Exception as e:
            print(f"✗ 检查 checkpoint 表出错: {str(e)}")
        
        print()
        
        # 2. 检查 roadmap_tasks 表
        print("2️⃣  检查 roadmap_tasks 表")
        print("-" * 70)
        try:
            # 总记录数
            result = await session.execute(
                select(func.count()).select_from(RoadmapTask)
            )
            total_count = result.scalar()
            print(f"总记录数: {total_count}")
            
            # 按状态分组
            result = await session.execute(
                text("""
                SELECT status, COUNT(*) as count 
                FROM roadmap_tasks 
                GROUP BY status
                """)
            )
            status_counts = result.fetchall()
            print("\n按状态分组:")
            for status, count in status_counts:
                print(f"  - {status}: {count}")
            
            # 最近5条记录
            result = await session.execute(
                select(RoadmapTask)
                .order_by(RoadmapTask.created_at.desc())
                .limit(5)
            )
            recent_tasks = result.scalars().all()
            
            print(f"\n最近 {len(recent_tasks)} 条任务:")
            for task in recent_tasks:
                print(f"  • {task.task_id[:16]}... [{task.status}] - {task.current_step}")
                print(f"    User: {task.user_id}")
                print(f"    Created: {task.created_at}")
                if task.roadmap_id:
                    print(f"    Roadmap: {task.roadmap_id}")
                print()
        except Exception as e:
            print(f"✗ 检查 roadmap_tasks 表出错: {str(e)}")
        
        print()
        
        # 3. 检查 roadmap_metadata 表
        print("3️⃣  检查 roadmap_metadata 表")
        print("-" * 70)
        try:
            # 总记录数
            result = await session.execute(
                select(func.count()).select_from(RoadmapMetadata)
            )
            total_count = result.scalar()
            print(f"总记录数: {total_count}")
            
            # 最近5条记录
            result = await session.execute(
                select(RoadmapMetadata)
                .order_by(RoadmapMetadata.created_at.desc())
                .limit(5)
            )
            recent_roadmaps = result.scalars().all()
            
            print(f"\n最近 {len(recent_roadmaps)} 个路线图:")
            for rm in recent_roadmaps:
                print(f"  • {rm.roadmap_id}")
                print(f"    Title: {rm.title}")
                print(f"    Task: {rm.task_id}")
                print(f"    User: {rm.user_id}")
                print(f"    Created: {rm.created_at}")
                
                # 检查是否有对应的教程
                tutorial_result = await session.execute(
                    select(func.count())
                    .select_from(TutorialMetadata)
                    .where(TutorialMetadata.roadmap_id == rm.roadmap_id)
                )
                tutorial_count = tutorial_result.scalar()
                print(f"    Tutorials: {tutorial_count}")
                print()
        except Exception as e:
            print(f"✗ 检查 roadmap_metadata 表出错: {str(e)}")
        
        print()
        
        # 4. 检查 tutorial_metadata 表
        print("4️⃣  检查 tutorial_metadata 表")
        print("-" * 70)
        try:
            # 总记录数
            result = await session.execute(
                select(func.count()).select_from(TutorialMetadata)
            )
            total_count = result.scalar()
            print(f"总记录数: {total_count}")
            
            # 按 roadmap_id 分组
            result = await session.execute(
                text("""
                SELECT roadmap_id, COUNT(*) as count 
                FROM tutorial_metadata 
                GROUP BY roadmap_id
                ORDER BY count DESC
                LIMIT 5
                """)
            )
            roadmap_counts = result.fetchall()
            
            if roadmap_counts:
                print(f"\n教程数量（按路线图）:")
                for roadmap_id, count in roadmap_counts:
                    print(f"  - {roadmap_id}: {count} 个教程")
            else:
                print("\n⚠️  没有教程记录")
            
            # 按状态分组
            result = await session.execute(
                text("""
                SELECT content_status, COUNT(*) as count 
                FROM tutorial_metadata 
                GROUP BY content_status
                """)
            )
            status_counts = result.fetchall()
            
            if status_counts:
                print(f"\n按状态分组:")
                for status, count in status_counts:
                    print(f"  - {status}: {count}")
            
        except Exception as e:
            print(f"✗ 检查 tutorial_metadata 表出错: {str(e)}")
    
    print()
    print("="*70)
    print("诊断完成")
    print("="*70)
    print()


async def test_specific_task(task_id: str = None):
    """测试特定任务的数据库记录"""
    if not task_id:
        print("请提供 task_id 参数")
        return
    
    print(f"\n检查任务: {task_id}\n")
    
    async with AsyncSessionLocal() as session:
        # 检查任务
        result = await session.execute(
            select(RoadmapTask).where(RoadmapTask.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            print(f"✗ 未找到任务 {task_id}")
            return
        
        print(f"✓ 找到任务:")
        print(f"  Status: {task.status}")
        print(f"  Current Step: {task.current_step}")
        print(f"  Roadmap ID: {task.roadmap_id}")
        print(f"  Created: {task.created_at}")
        print(f"  Updated: {task.updated_at}")
        
        if task.roadmap_id:
            # 检查路线图
            result = await session.execute(
                select(RoadmapMetadata).where(RoadmapMetadata.roadmap_id == task.roadmap_id)
            )
            metadata = result.scalar_one_or_none()
            
            if metadata:
                print(f"\n✓ 找到路线图元数据:")
                print(f"  Title: {metadata.title}")
                print(f"  Stages: {len(metadata.framework_data.get('stages', []))}")
                
                # 检查教程
                result = await session.execute(
                    select(func.count())
                    .select_from(TutorialMetadata)
                    .where(TutorialMetadata.roadmap_id == task.roadmap_id)
                )
                tutorial_count = result.scalar()
                print(f"  Tutorials: {tutorial_count}")
            else:
                print(f"\n✗ 未找到路线图元数据")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 检查特定任务
        asyncio.run(test_specific_task(sys.argv[1]))
    else:
        # 全面诊断
        asyncio.run(diagnose_database())





















