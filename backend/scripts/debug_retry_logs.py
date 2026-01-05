"""
调试脚本：检查重试任务的执行日志

检查为什么 retry 任务的 execution_logs 中 step 字段为 null
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from sqlalchemy import select, and_
from app.db.session import get_async_session_context
from app.models.database import ExecutionLog

logger = structlog.get_logger()


async def check_retry_logs(task_id: str = None):
    """
    检查重试任务的执行日志
    
    Args:
        task_id: 任务 ID（可选，如果不提供则查询最近的重试日志）
    """
    print(f"\n{'='*80}")
    print(f"检查重试任务的执行日志")
    print(f"{'='*80}\n")
    
    async with get_async_session_context() as session:
        # 构建查询
        if task_id:
            # 查询指定任务的日志
            stmt = (
                select(ExecutionLog)
                .where(ExecutionLog.task_id == task_id)
                .order_by(ExecutionLog.created_at.desc())
                .limit(50)
            )
            print(f"查询任务 {task_id} 的日志...\n")
        else:
            # 查询最近的重试相关日志
            stmt = (
                select(ExecutionLog)
                .where(
                    and_(
                        ExecutionLog.category == "workflow",
                        ExecutionLog.message.like("%retry%")
                    )
                )
                .order_by(ExecutionLog.created_at.desc())
                .limit(50)
            )
            print(f"查询最近的重试相关日志...\n")
        
        result = await session.execute(stmt)
        logs = list(result.scalars().all())
        
        if not logs:
            print("❌ 没有找到相关日志")
            return
        
        print(f"✅ 找到 {len(logs)} 条日志\n")
        
        # 统计 step 为 null 的日志
        null_step_count = sum(1 for log in logs if log.step is None)
        print(f"📊 统计:")
        print(f"   - 总日志数: {len(logs)}")
        print(f"   - step 为 null: {null_step_count}")
        print(f"   - step 有值: {len(logs) - null_step_count}")
        
        # 显示前 10 条日志的详细信息
        print(f"\n🔍 前 10 条日志详情:\n")
        for i, log in enumerate(logs[:10], 1):
            print(f"日志 {i}:")
            print(f"   - ID: {log.id}")
            print(f"   - task_id: {log.task_id}")
            print(f"   - category: {log.category}")
            print(f"   - level: {log.level}")
            print(f"   - step: {log.step if log.step else '❌ NULL'}")
            print(f"   - message: {log.message[:100]}")
            print(f"   - created_at: {log.created_at}")
            
            if log.roadmap_id:
                print(f"   - roadmap_id: {log.roadmap_id}")
            if log.concept_id:
                print(f"   - concept_id: {log.concept_id}")
            if log.agent_name:
                print(f"   - agent_name: {log.agent_name}")
            
            print()
        
        # 检查是否有 retry 相关的 step 值
        retry_steps = set()
        for log in logs:
            if log.step and "retry" in log.step:
                retry_steps.add(log.step)
        
        if retry_steps:
            print(f"✅ 找到以下 retry 相关的 step 值:")
            for step in sorted(retry_steps):
                count = sum(1 for log in logs if log.step == step)
                print(f"   - {step}: {count} 条")
        else:
            print(f"⚠️  没有找到 retry 相关的 step 值")
        
        print(f"\n{'='*80}")
        print(f"检查完成")
        print(f"{'='*80}\n")


async def main():
    """主函数"""
    task_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if task_id:
        print(f"检查任务: {task_id}")
    else:
        print("未指定任务 ID，将查询最近的重试日志")
        print("用法: python debug_retry_logs.py [task_id]")
    
    try:
        await check_retry_logs(task_id)
    except Exception as e:
        logger.error("check_failed", error=str(e))
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

