"""批准所有等待人工审核的任务，触发教程生成"""
import asyncio
import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.database import RoadmapTask
from app.core.orchestrator import RoadmapOrchestrator
from app.db.repositories.roadmap_repo import RoadmapRepository
import structlog

logger = structlog.get_logger()


async def approve_all_pending_tasks():
    """批准所有等待人工审核的任务"""
    # 初始化 orchestrator
    await RoadmapOrchestrator.initialize()
    orchestrator = RoadmapOrchestrator()
    
    try:
        async with AsyncSessionLocal() as session:
            # 查询所有等待人工审核的任务
            result = await session.execute(
                select(RoadmapTask)
                .where(RoadmapTask.status == "human_review_pending")
                .order_by(RoadmapTask.created_at.desc())
            )
            pending_tasks = result.scalars().all()
            
            print(f"\n=== 找到 {len(pending_tasks)} 个等待审核的任务 ===\n")
            
            if not pending_tasks:
                print("没有等待审核的任务")
                return
            
            repo = RoadmapRepository(session)
            
            for i, task in enumerate(pending_tasks, 1):
                print(f"[{i}/{len(pending_tasks)}] 处理任务: {task.task_id}")
                print(f"  Roadmap ID: {task.roadmap_id}")
                print(f"  创建时间: {task.created_at}")
                
                try:
                    # 恢复工作流并批准
                    print(f"  正在批准并继续工作流...")
                    final_state = await orchestrator.resume_after_human_review(
                        task_id=task.task_id,
                        approved=True,
                        feedback=None,
                    )
                    
                    # 保存路线图和教程元数据
                    if final_state.get("roadmap_framework"):
                        framework = final_state["roadmap_framework"]
                        
                        # 保存路线图元数据
                        await repo.save_roadmap_metadata(
                            roadmap_id=framework.roadmap_id,
                            user_id=task.user_id,
                            task_id=task.task_id,
                            framework=framework,
                        )
                        
                        # 保存教程元数据（如果存在）
                        tutorial_refs = final_state.get("tutorial_refs", {})
                        if tutorial_refs:
                            print(f"  正在保存 {len(tutorial_refs)} 个教程元数据...")
                            await repo.save_tutorials_batch(
                                tutorial_refs=tutorial_refs,
                                roadmap_id=framework.roadmap_id,
                            )
                            print(f"  ✓ 成功保存 {len(tutorial_refs)} 个教程元数据")
                        else:
                            print(f"  ⚠ 没有生成教程")
                        
                        # 更新任务状态为完成
                        await repo.update_task_status(
                            task_id=task.task_id,
                            status="completed",
                            current_step="completed",
                            roadmap_id=framework.roadmap_id,
                        )
                        print(f"  ✓ 任务已完成\n")
                    else:
                        print(f"  ✗ 路线图框架不存在\n")
                        # 更新任务状态为失败
                        await repo.update_task_status(
                            task_id=task.task_id,
                            status="failed",
                            current_step="failed",
                            error_message="路线图框架生成失败",
                        )
                    
                    await session.commit()
                    
                except Exception as e:
                    logger.error(
                        "approve_task_failed",
                        task_id=task.task_id,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    print(f"  ✗ 处理失败: {str(e)}\n")
                    
                    # 更新任务状态为失败
                    await repo.update_task_status(
                        task_id=task.task_id,
                        status="failed",
                        current_step="failed",
                        error_message=str(e),
                    )
                    await session.commit()
                    continue
        
        print("\n=== 批准完成 ===")
        
    finally:
        # 关闭 orchestrator
        await RoadmapOrchestrator.shutdown()


async def approve_single_task(task_id: str):
    """批准单个任务"""
    # 初始化 orchestrator
    await RoadmapOrchestrator.initialize()
    orchestrator = RoadmapOrchestrator()
    
    try:
        async with AsyncSessionLocal() as session:
            # 查询任务
            result = await session.execute(
                select(RoadmapTask).where(RoadmapTask.task_id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                print(f"任务 {task_id} 不存在")
                return
            
            if task.status != "human_review_pending":
                print(f"任务 {task_id} 当前状态为 {task.status}，不是 human_review_pending")
                return
            
            print(f"\n=== 批准任务: {task.task_id} ===")
            print(f"Roadmap ID: {task.roadmap_id}")
            print(f"创建时间: {task.created_at}\n")
            
            repo = RoadmapRepository(session)
            
            try:
                # 恢复工作流并批准
                print("正在批准并继续工作流...")
                final_state = await orchestrator.resume_after_human_review(
                    task_id=task.task_id,
                    approved=True,
                    feedback=None,
                )
                
                # 保存路线图和教程元数据
                if final_state.get("roadmap_framework"):
                    framework = final_state["roadmap_framework"]
                    
                    # 保存路线图元数据
                    await repo.save_roadmap_metadata(
                        roadmap_id=framework.roadmap_id,
                        user_id=task.user_id,
                        task_id=task.task_id,
                        framework=framework,
                    )
                    
                    # 保存教程元数据（如果存在）
                    tutorial_refs = final_state.get("tutorial_refs", {})
                    if tutorial_refs:
                        print(f"正在保存 {len(tutorial_refs)} 个教程元数据...")
                        await repo.save_tutorials_batch(
                            tutorial_refs=tutorial_refs,
                            roadmap_id=framework.roadmap_id,
                        )
                        print(f"✓ 成功保存 {len(tutorial_refs)} 个教程元数据")
                    else:
                        print("⚠ 没有生成教程")
                    
                    # 更新任务状态为完成
                    await repo.update_task_status(
                        task_id=task.task_id,
                        status="completed",
                        current_step="completed",
                        roadmap_id=framework.roadmap_id,
                    )
                    print("✓ 任务已完成")
                else:
                    print("✗ 路线图框架不存在")
                    # 更新任务状态为失败
                    await repo.update_task_status(
                        task_id=task.task_id,
                        status="failed",
                        current_step="failed",
                        error_message="路线图框架生成失败",
                    )
                
                await session.commit()
                
            except Exception as e:
                logger.error(
                    "approve_task_failed",
                    task_id=task.task_id,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                print(f"✗ 处理失败: {str(e)}")
                
                # 更新任务状态为失败
                await repo.update_task_status(
                    task_id=task.task_id,
                    status="failed",
                    current_step="failed",
                    error_message=str(e),
                )
                await session.commit()
    
    finally:
        # 关闭 orchestrator
        await RoadmapOrchestrator.shutdown()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # 批准单个任务
        task_id = sys.argv[1]
        asyncio.run(approve_single_task(task_id))
    else:
        # 批准所有等待审核的任务
        asyncio.run(approve_all_pending_tasks())

