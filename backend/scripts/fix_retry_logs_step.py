"""
修复脚本：更新重试任务执行日志的 step 字段

将 retry 相关的日志中 step=null 的记录根据 message 内容推断并更新
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from sqlalchemy import select, and_, update
from app.db.session import get_async_session_context
from app.models.database import ExecutionLog

logger = structlog.get_logger()


async def fix_retry_logs_step(dry_run: bool = True):
    """
    修复重试任务日志的 step 字段
    
    Args:
        dry_run: 是否为干运行模式（不实际更新数据库）
    """
    print(f"\n{'='*80}")
    print(f"修复重试任务日志的 step 字段")
    print(f"模式: {'DRY RUN (不会修改数据库)' if dry_run else '实际执行 (会修改数据库)'}")
    print(f"{'='*80}\n")
    
    async with get_async_session_context() as session:
        # 查询 step 为 null 且 message 包含 retry 的日志
        stmt = (
            select(ExecutionLog)
            .where(
                and_(
                    ExecutionLog.step.is_(None),
                    ExecutionLog.category == "workflow",
                    ExecutionLog.message.like("%retry%")
                )
            )
            .order_by(ExecutionLog.created_at.desc())
        )
        
        result = await session.execute(stmt)
        logs = list(result.scalars().all())
        
        if not logs:
            print("✅ 没有找到需要修复的日志")
            return
        
        print(f"找到 {len(logs)} 条需要修复的日志\n")
        
        # 推断 step 值：所有重试相关的日志都应该使用 content_generation
        updates = []
        for log in logs:
            message_lower = log.message.lower()
            inferred_step = None
            
            # 所有重试任务都使用 content_generation 这一个枚举值
            if "retry" in message_lower or "regenerat" in message_lower:
                inferred_step = "content_generation"
            
            if inferred_step:
                updates.append({
                    "id": log.id,
                    "task_id": log.task_id,
                    "message": log.message[:80],
                    "inferred_step": inferred_step,
                    "created_at": log.created_at,
                })
        
        if not updates:
            print("⚠️  无法推断任何日志的 step 值")
            return
        
        print(f"可以推断 {len(updates)} 条日志的 step 值:\n")
        
        # 按 step 分组统计
        step_counts = {}
        for update in updates:
            step = update["inferred_step"]
            step_counts[step] = step_counts.get(step, 0) + 1
        
        for step, count in sorted(step_counts.items()):
            print(f"   - {step}: {count} 条")
        
        # 显示前 5 条示例
        print(f"\n前 5 条示例:")
        for i, update in enumerate(updates[:5], 1):
            print(f"\n   {i}. ID: {update['id']}")
            print(f"      task_id: {update['task_id']}")
            print(f"      message: {update['message']}")
            print(f"      推断的 step: {update['inferred_step']}")
            print(f"      created_at: {update['created_at']}")
        
        if dry_run:
            print(f"\n⚠️  DRY RUN 模式，不会实际更新数据库")
            print(f"   如需实际执行，请运行: python fix_retry_logs_step.py --execute")
        else:
            print(f"\n开始更新数据库...")
            
            # 批量更新
            updated_count = 0
            for update in updates:
                stmt = (
                    update(ExecutionLog)
                    .where(ExecutionLog.id == update["id"])
                    .values(step=update["inferred_step"])
                )
                await session.execute(stmt)
                updated_count += 1
            
            await session.commit()
            
            print(f"✅ 成功更新 {updated_count} 条日志")
        
        print(f"\n{'='*80}")
        print(f"修复完成")
        print(f"{'='*80}\n")


async def main():
    """主函数"""
    # 检查命令行参数
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        dry_run = False
        print("⚠️  实际执行模式，将会修改数据库！")
        print("按 Ctrl+C 取消，或等待 3 秒后继续...")
        await asyncio.sleep(3)
    
    try:
        await fix_retry_logs_step(dry_run=dry_run)
    except Exception as e:
        logger.error("fix_failed", error=str(e))
        print(f"\n❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

