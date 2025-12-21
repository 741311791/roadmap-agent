#!/usr/bin/env python3
"""
清理 intent_analysis_metadata 表中的重复记录

问题：task_id 字段没有唯一性约束，导致可以插入重复记录
解决：
1. 保留每个 task_id 的最新记录（按 created_at 排序）
2. 删除重复的旧记录
3. 添加唯一性约束（在数据库模型中已添加，需要运行 alembic migrate）

使用方法：
    python backend/scripts/fix_duplicate_intent_analysis.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models.database import IntentAnalysisMetadata
import structlog

logger = structlog.get_logger()


async def find_duplicates(session: AsyncSession) -> dict[str, list[str]]:
    """
    查找重复的 task_id 及其对应的记录 ID
    
    Returns:
        字典: {task_id: [id1, id2, ...]}，其中 id 按 created_at 降序排列（最新的在前）
    """
    # 查找有重复的 task_id
    stmt = (
        select(
            IntentAnalysisMetadata.task_id,
            func.count(IntentAnalysisMetadata.id).label('count')
        )
        .group_by(IntentAnalysisMetadata.task_id)
        .having(func.count(IntentAnalysisMetadata.id) > 1)
    )
    
    result = await session.execute(stmt)
    duplicate_task_ids = [row[0] for row in result.all()]
    
    if not duplicate_task_ids:
        logger.info("no_duplicates_found")
        return {}
    
    logger.info(
        "duplicates_found",
        count=len(duplicate_task_ids),
        task_ids=duplicate_task_ids,
    )
    
    # 获取每个重复 task_id 的所有记录（按 created_at 降序）
    duplicates = {}
    for task_id in duplicate_task_ids:
        stmt = (
            select(IntentAnalysisMetadata)
            .where(IntentAnalysisMetadata.task_id == task_id)
            .order_by(IntentAnalysisMetadata.created_at.desc())
        )
        result = await session.execute(stmt)
        records = result.scalars().all()
        
        duplicates[task_id] = [
            {
                'id': record.id,
                'created_at': record.created_at,
                'roadmap_id': record.roadmap_id,
            }
            for record in records
        ]
        
        logger.info(
            "duplicate_details",
            task_id=task_id,
            records_count=len(records),
            records=[
                f"ID: {r['id'][:8]}... | Created: {r['created_at']} | Roadmap: {r['roadmap_id']}"
                for r in duplicates[task_id]
            ],
        )
    
    return duplicates


async def clean_duplicates(session: AsyncSession, duplicates: dict[str, list[dict]]) -> int:
    """
    清理重复记录，保留最新的一条
    
    Args:
        session: 数据库会话
        duplicates: 重复记录字典
        
    Returns:
        删除的记录数量
    """
    deleted_count = 0
    
    for task_id, records in duplicates.items():
        # 保留第一条（最新的），删除其余的
        to_delete = records[1:]  # 跳过第一条
        
        logger.info(
            "cleaning_duplicates_for_task",
            task_id=task_id,
            keeping=records[0]['id'][:8] + "...",
            deleting_count=len(to_delete),
        )
        
        for record in to_delete:
            stmt = select(IntentAnalysisMetadata).where(
                IntentAnalysisMetadata.id == record['id']
            )
            result = await session.execute(stmt)
            record_to_delete = result.scalar_one_or_none()
            
            if record_to_delete:
                await session.delete(record_to_delete)
                deleted_count += 1
                logger.info(
                    "deleted_duplicate_record",
                    task_id=task_id,
                    id=record['id'][:8] + "...",
                    created_at=record['created_at'],
                )
    
    return deleted_count


async def main():
    """主函数"""
    logger.info("fix_duplicate_intent_analysis_started")
    
    async with AsyncSessionLocal() as session:
        try:
            # 1. 查找重复记录
            logger.info("step_1_finding_duplicates")
            duplicates = await find_duplicates(session)
            
            if not duplicates:
                logger.info("no_action_needed")
                return
            
            # 2. 清理重复记录
            logger.info("step_2_cleaning_duplicates")
            deleted_count = await clean_duplicates(session, duplicates)
            
            # 3. 提交事务
            logger.info("step_3_committing_changes")
            await session.commit()
            
            logger.info(
                "fix_duplicate_intent_analysis_completed",
                deleted_count=deleted_count,
                cleaned_task_ids=list(duplicates.keys()),
            )
            
            print(f"\n✅ 清理完成！删除了 {deleted_count} 条重复记录。")
            print(f"   涉及的 task_id: {', '.join(list(duplicates.keys())[:5])}")
            if len(duplicates) > 5:
                print(f"   ... 以及其他 {len(duplicates) - 5} 个")
            
        except Exception as e:
            await session.rollback()
            logger.error(
                "fix_duplicate_intent_analysis_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            print(f"\n❌ 清理失败: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(main())

