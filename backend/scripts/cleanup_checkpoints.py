"""
清理 LangGraph Checkpoint 数据

功能：
1. 清理指定天数之前的 checkpoint 数据
2. 清理已完成/失败任务的 checkpoint 数据
3. 显示当前 checkpoint 表的统计信息

使用场景：
- checkpoint 表数据量过大，导致查询慢
- 定期清理历史数据，释放存储空间
"""
import asyncio
import structlog
from datetime import datetime, timedelta
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config.settings import settings
from app.models.database import Task
from app.models.constants import TaskStatus

logger = structlog.get_logger()


async def get_checkpoint_stats(db: AsyncSession) -> dict:
    """
    获取 checkpoint 表统计信息
    
    Returns:
        统计信息字典
    """
    try:
        # 查询 checkpoint 表的记录数
        result = await db.execute(
            text("SELECT COUNT(*) FROM checkpoints")
        )
        total_count = result.scalar_one()
        
        # 查询 checkpoint 表的大小
        result = await db.execute(
            text("""
                SELECT pg_size_pretty(pg_total_relation_size('checkpoints')) as size
            """)
        )
        table_size = result.scalar_one()
        
        return {
            "total_count": total_count,
            "table_size": table_size,
        }
    except Exception as e:
        logger.error("get_checkpoint_stats_failed", error=str(e))
        return {"total_count": 0, "table_size": "unknown"}


async def cleanup_old_checkpoints(db: AsyncSession, days: int = 7) -> int:
    """
    清理指定天数之前的 checkpoint 数据
    
    Args:
        db: 数据库会话
        days: 保留最近N天的数据
        
    Returns:
        删除的记录数
    """
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    
    try:
        result = await db.execute(
            text("""
                DELETE FROM checkpoints
                WHERE checkpoint->>'ts' < :cutoff_time
            """),
            {"cutoff_time": cutoff_time.isoformat()}
        )
        await db.commit()
        
        deleted_count = result.rowcount
        logger.info(
            "cleanup_old_checkpoints_success",
            days=days,
            cutoff_time=cutoff_time.isoformat(),
            deleted_count=deleted_count,
        )
        return deleted_count
    except Exception as e:
        await db.rollback()
        logger.error(
            "cleanup_old_checkpoints_failed",
            error=str(e),
            days=days,
        )
        return 0


async def cleanup_completed_task_checkpoints(db: AsyncSession) -> int:
    """
    清理已完成/失败任务的 checkpoint 数据
    
    Args:
        db: 数据库会话
        
    Returns:
        删除的记录数
    """
    try:
        # 查询所有已完成/失败的任务ID
        result = await db.execute(
            select(Task.task_id).where(
                Task.status.in_([
                    TaskStatus.COMPLETED,
                    TaskStatus.FAILED,
                    TaskStatus.CANCELLED,
                ])
            )
        )
        finished_task_ids = [row[0] for row in result.all()]
        
        if not finished_task_ids:
            logger.info("no_finished_tasks_to_cleanup")
            return 0
        
        # 删除这些任务的 checkpoint 数据
        # LangGraph 使用 thread_id 来存储 checkpoint，格式为 task_id
        result = await db.execute(
            text("""
                DELETE FROM checkpoints
                WHERE thread_id = ANY(:task_ids)
            """),
            {"task_ids": finished_task_ids}
        )
        await db.commit()
        
        deleted_count = result.rowcount
        logger.info(
            "cleanup_completed_task_checkpoints_success",
            finished_tasks_count=len(finished_task_ids),
            deleted_count=deleted_count,
        )
        return deleted_count
    except Exception as e:
        await db.rollback()
        logger.error(
            "cleanup_completed_task_checkpoints_failed",
            error=str(e),
        )
        return 0


async def main():
    """主函数"""
    # 配置日志
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
    
    # 创建数据库引擎
    engine = create_async_engine(
        settings.CHECKPOINTER_DATABASE_URL,
        echo=False,
    )
    
    async_session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session_maker() as db:
        print("\n" + "=" * 60)
        print("📊 Checkpoint 数据统计")
        print("=" * 60)
        
        # 1. 显示统计信息
        stats = await get_checkpoint_stats(db)
        print(f"  总记录数: {stats['total_count']}")
        print(f"  表大小: {stats['table_size']}")
        
        # 2. 清理已完成/失败任务的 checkpoint
        print("\n" + "=" * 60)
        print("🧹 清理已完成/失败任务的 Checkpoint 数据")
        print("=" * 60)
        
        deleted_count = await cleanup_completed_task_checkpoints(db)
        print(f"  ✅ 删除了 {deleted_count} 条记录")
        
        # 3. 清理旧数据（可选）
        print("\n" + "=" * 60)
        print("🧹 清理 7 天前的 Checkpoint 数据（可选）")
        print("=" * 60)
        
        # 询问用户是否清理旧数据
        response = input("  是否清理 7 天前的数据? (y/n): ")
        if response.lower() == 'y':
            deleted_count = await cleanup_old_checkpoints(db, days=7)
            print(f"  ✅ 删除了 {deleted_count} 条记录")
        else:
            print("  ⏭️  跳过旧数据清理")
        
        # 4. 再次显示统计信息
        print("\n" + "=" * 60)
        print("📊 清理后的统计信息")
        print("=" * 60)
        
        stats = await get_checkpoint_stats(db)
        print(f"  总记录数: {stats['total_count']}")
        print(f"  表大小: {stats['table_size']}")
        print("\n✅ 清理完成！\n")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
