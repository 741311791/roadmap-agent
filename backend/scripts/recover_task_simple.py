"""
简化的任务恢复脚本（避免循环导入）

直接使用任务恢复服务的核心逻辑来恢复任务
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import structlog

logger = structlog.get_logger()


async def recover_task(task_id: str):
    """
    恢复指定任务
    
    Args:
        task_id: 任务 ID
    """
    logger.info("starting_task_recovery", task_id=task_id)
    
    # 延迟导入所有模块，避免循环依赖
    from app.core.dependencies import init_orchestrator, cleanup_orchestrator
    from app.core.orchestrator_factory import OrchestratorFactory
    from app.db.repository_factory import RepositoryFactory
    
    try:
        # 初始化 orchestrator
        logger.info("initializing_orchestrator")
        await init_orchestrator()
        
        # 1. 查询任务
        repo_factory = RepositoryFactory()
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            task = await task_repo.get_by_task_id(task_id)
            
            if not task:
                print(f"\n❌ 任务 {task_id} 不存在")
                return
            
            if task.status != "processing":
                print(f"\n⚠️  任务 {task_id} 的状态是 {task.status}，不是 processing")
                print("   只有 processing 状态的任务才能从 checkpoint 恢复")
                return
            
            print(f"\n📋 任务信息：")
            print(f"   任务 ID: {task.task_id}")
            print(f"   当前步骤: {task.current_step}")
            print(f"   路线图 ID: {task.roadmap_id}")
            print(f"   创建时间: {task.created_at}")
            print()
        
        # 2. 检查 checkpoint
        print("🔍 检查 checkpoint...")
        checkpointer = OrchestratorFactory.get_checkpointer()
        config = {"configurable": {"thread_id": task_id}}
        checkpoint_tuple = await checkpointer.aget_tuple(config)
        
        if not checkpoint_tuple or not checkpoint_tuple.checkpoint:
            print("❌ 任务没有 checkpoint，无法恢复")
            print("   可能的原因：")
            print("   - checkpoint 已被清理")
            print("   - 任务从未成功保存过 checkpoint")
            return
        
        channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
        checkpoint_step = channel_values.get("current_step", "unknown")
        
        print(f"✅ 找到 checkpoint，当前步骤: {checkpoint_step}")
        print()
        
        # 3. 发送恢复通知
        print("📢 发送恢复通知...")
        from app.services.notification_service import notification_service
        await notification_service.notify_task_recovering(
            task_id=task_id,
            roadmap_id=task.roadmap_id,
            current_step=checkpoint_step,
        )
        
        # 4. 从 checkpoint 恢复执行
        print("🚀 开始恢复执行...")
        executor = OrchestratorFactory.create_workflow_executor()
        
        # LangGraph 恢复机制：传入 None 会从最后的 checkpoint 继续执行
        final_state = await executor.graph.ainvoke(None, config=config)
        
        final_step = final_state.get("current_step", "unknown")
        roadmap_id = final_state.get("roadmap_id")
        
        print(f"✅ 恢复完成！")
        print(f"   最终步骤: {final_step}")
        print(f"   路线图 ID: {roadmap_id}")
        
        # 清除 live_step 缓存
        executor.state_manager.clear_live_step(task_id)
        
        print("\n🎉 任务恢复成功！")
        
    except Exception as e:
        logger.error(
            "recovery_failed",
            task_id=task_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        print(f"\n❌ 恢复失败: {str(e)}")
        print(f"   错误类型: {type(e).__name__}")
        import traceback
        print("\n详细错误信息：")
        traceback.print_exc()
        raise
    
    finally:
        # 清理 orchestrator
        logger.info("cleaning_up_orchestrator")
        await cleanup_orchestrator()


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="从 checkpoint 恢复任务")
    parser.add_argument("task_id", help="要恢复的任务 ID")
    
    args = parser.parse_args()
    
    await recover_task(args.task_id)


if __name__ == "__main__":
    asyncio.run(main())

