"""
手动从 checkpoint 恢复任务脚本

用途：
- 当任务状态为 processing 但后端没有任务在运行时，手动触发恢复
- 适用于服务器重启后任务未自动恢复的情况
- 适用于连接池问题导致任务中断的情况

使用方法：
    # 恢复所有 processing 状态的任务
    python scripts/recover_task_from_checkpoint.py

    # 恢复指定任务
    python scripts/recover_task_from_checkpoint.py --task-id <task_id>

    # 查看所有 processing 状态的任务（不恢复）
    python scripts/recover_task_from_checkpoint.py --list-only
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog
from app.config.settings import settings
from app.db.repository_factory import RepositoryFactory
from app.models.database import RoadmapTask

logger = structlog.get_logger()


async def check_checkpoint_exists(task_id: str) -> tuple[bool, str | None]:
    """
    检查任务的 checkpoint 是否存在
    
    Args:
        task_id: 任务 ID
        
    Returns:
        (是否存在, checkpoint 中的当前步骤)
    """
    try:
        # 延迟导入避免循环依赖
        from app.core.orchestrator_factory import OrchestratorFactory
        
        checkpointer = OrchestratorFactory.get_checkpointer()
        config = {"configurable": {"thread_id": task_id}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        
        if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
            return False, None
        
        channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
        checkpoint_step = channel_values.get("current_step", "unknown")
        return True, checkpoint_step
        
    except Exception as e:
        logger.error(
            "checkpoint_check_failed",
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False, None


async def recover_single_task(task: RoadmapTask) -> str:
    """
    恢复单个任务
    
    Args:
        task: 要恢复的任务
        
    Returns:
        恢复结果：'recovered', 'no_checkpoint', 'failed'
    """
    task_id = task.task_id
    
    logger.info(
        "recovering_task",
        task_id=task_id,
        current_step=task.current_step,
        roadmap_id=task.roadmap_id,
        created_at=task.created_at.isoformat() if task.created_at else None,
    )
    
    # 1. 检查 checkpoint 是否存在
    checkpoint_exists, checkpoint_step = await check_checkpoint_exists(task_id)
    
    if not checkpoint_exists:
        logger.warning(
            "no_checkpoint_found",
            task_id=task_id,
            message="任务没有 checkpoint，无法恢复",
        )
        return "no_checkpoint"
    
    logger.info(
        "checkpoint_found",
        task_id=task_id,
        checkpoint_step=checkpoint_step,
    )
    
    # 2. 创建 executor 并从 checkpoint 恢复
    try:
        # 延迟导入避免循环依赖
        from app.core.orchestrator_factory import OrchestratorFactory
        from app.services.notification_service import notification_service
        
        executor = OrchestratorFactory.create_workflow_executor()
        config = {"configurable": {"thread_id": task_id}}
        
        # 发送恢复通知
        await notification_service.notify_task_recovering(
            task_id=task_id,
            roadmap_id=task.roadmap_id,
            current_step=checkpoint_step or task.current_step,
        )
        
        logger.info(
            "starting_recovery_execution",
            task_id=task_id,
            checkpoint_step=checkpoint_step,
        )
        
        # LangGraph 恢复机制：传入 None 会从最后的 checkpoint 继续执行
        final_state = await executor.graph.ainvoke(None, config=config)
        
        final_step = final_state.get("current_step", "unknown")
        roadmap_id = final_state.get("roadmap_id")
        
        logger.info(
            "recovery_completed",
            task_id=task_id,
            final_step=final_step,
            roadmap_id=roadmap_id,
        )
        
        # 清除 live_step 缓存
        executor.state_manager.clear_live_step(task_id)
        
        return "recovered"
        
    except Exception as e:
        logger.error(
            "recovery_failed",
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        return "failed"


async def list_processing_tasks(max_age_hours: int = 24) -> list[RoadmapTask]:
    """
    列出所有 processing 状态的任务
    
    Args:
        max_age_hours: 任务最大年龄（小时）
        
    Returns:
        任务列表
    """
    repo_factory = RepositoryFactory()
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        tasks = await task_repo.find_interrupted_tasks(max_age_hours=max_age_hours)
        return tasks


async def get_task_by_id(task_id: str) -> RoadmapTask | None:
    """
    根据任务 ID 获取任务
    
    Args:
        task_id: 任务 ID
        
    Returns:
        任务对象，如果不存在则返回 None
    """
    repo_factory = RepositoryFactory()
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        return await task_repo.get_by_task_id(task_id)


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="从 checkpoint 恢复任务",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--task-id",
        type=str,
        help="要恢复的任务 ID（如果不指定，则恢复所有 processing 状态的任务）",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="只列出 processing 状态的任务，不执行恢复",
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=24,
        help="任务最大年龄（小时），默认 24 小时",
    )
    
    args = parser.parse_args()
    
    # 初始化 orchestrator（延迟导入避免循环依赖）
    logger.info("initializing_orchestrator")
    from app.core.dependencies import init_orchestrator, cleanup_orchestrator
    await init_orchestrator()
    
    try:
        if args.list_only:
            # 只列出任务
            logger.info("listing_processing_tasks", max_age_hours=args.max_age_hours)
            tasks = await list_processing_tasks(max_age_hours=args.max_age_hours)
            
            if not tasks:
                print("\n✅ 没有找到 processing 状态的任务")
                return
            
            print(f"\n📋 找到 {len(tasks)} 个 processing 状态的任务：\n")
            
            for i, task in enumerate(tasks, 1):
                checkpoint_exists, checkpoint_step = await check_checkpoint_exists(task.task_id)
                checkpoint_status = "✅ 有 checkpoint" if checkpoint_exists else "❌ 无 checkpoint"
                checkpoint_info = f" (checkpoint 步骤: {checkpoint_step})" if checkpoint_exists else ""
                
                print(f"{i}. 任务 ID: {task.task_id}")
                print(f"   当前步骤: {task.current_step}")
                print(f"   路线图 ID: {task.roadmap_id}")
                print(f"   创建时间: {task.created_at}")
                print(f"   Checkpoint: {checkpoint_status}{checkpoint_info}")
                print()
            
        elif args.task_id:
            # 恢复指定任务
            logger.info("recovering_specific_task", task_id=args.task_id)
            task = await get_task_by_id(args.task_id)
            
            if not task:
                print(f"\n❌ 任务 {args.task_id} 不存在")
                return
            
            if task.status != "processing":
                print(f"\n⚠️  任务 {args.task_id} 的状态是 {task.status}，不是 processing")
                print("   只有 processing 状态的任务才能从 checkpoint 恢复")
                return
            
            result = await recover_single_task(task)
            
            if result == "recovered":
                print(f"\n✅ 任务 {args.task_id} 恢复成功")
            elif result == "no_checkpoint":
                print(f"\n❌ 任务 {args.task_id} 没有 checkpoint，无法恢复")
            else:
                print(f"\n❌ 任务 {args.task_id} 恢复失败，请查看日志")
        
        else:
            # 恢复所有 processing 状态的任务
            logger.info("recovering_all_processing_tasks", max_age_hours=args.max_age_hours)
            tasks = await list_processing_tasks(max_age_hours=args.max_age_hours)
            
            if not tasks:
                print("\n✅ 没有找到 processing 状态的任务")
                return
            
            print(f"\n📋 找到 {len(tasks)} 个 processing 状态的任务，开始恢复...\n")
            
            results = {
                "recovered": 0,
                "no_checkpoint": 0,
                "failed": 0,
            }
            
            for i, task in enumerate(tasks, 1):
                print(f"[{i}/{len(tasks)}] 恢复任务 {task.task_id}...")
                result = await recover_single_task(task)
                results[result] = results.get(result, 0) + 1
                
                # 添加延迟，避免同时恢复太多任务造成压力
                if i < len(tasks):
                    await asyncio.sleep(2)
            
            print("\n" + "=" * 60)
            print("恢复结果汇总：")
            print(f"  ✅ 成功恢复: {results.get('recovered', 0)}")
            print(f"  ❌ 无 checkpoint: {results.get('no_checkpoint', 0)}")
            print(f"  ⚠️  恢复失败: {results.get('failed', 0)}")
            print("=" * 60)
    
    finally:
        # 清理 orchestrator
        logger.info("cleaning_up_orchestrator")
        from app.core.dependencies import cleanup_orchestrator
        await cleanup_orchestrator()


if __name__ == "__main__":
    asyncio.run(main())

