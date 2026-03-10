#!/usr/bin/env python3
"""
修复卡在 content_generation_queued 状态的任务

问题根因：
- task_acks_late=True + visibility_timeout=7200s (2小时)
- Worker 被强制 Kill 后，任务进入 Redis unacked 有序集合
- 2小时内不会自动重新入队，但 DB 状态永久显示 "processing"

使用方式：
    cd backend
    uv run python scripts/recover_stuck_content_generation.py <task_id> <roadmap_id> <user_id> [old_celery_task_id]

示例：
    uv run python scripts/recover_stuck_content_generation.py \
        cbe6dc97-45bc-49ae-a9dc-65b4f46275a3 \
        post-trainingcptsftrl-36289c07 \
        1870910d-727b-4e02-bd43-fd095c4d2484 \
        7de0cae7-9b8e-4982-bdf3-b3c7b6cd0c0e
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def recover(
    task_id: str,
    roadmap_id: str,
    user_id: str,
    old_celery_task_id: str | None = None,
) -> None:
    from app.core.celery_app import celery_app
    from app.tasks.content_generation_tasks import generate_all_content_task
    from app.db.celery_session import get_celery_session
    from app.crud.crud_task import get_task_crud

    print(f"\n🔧 恢复任务: {task_id}")
    print(f"   roadmap_id: {roadmap_id}")
    print(f"   user_id:    {user_id}")
    if old_celery_task_id:
        print(f"   旧 Celery ID: {old_celery_task_id}")
    print()

    # 第一步：Revoke 旧的 Celery 任务（防止 2h 后 visibility_timeout 到期时重复执行）
    if old_celery_task_id:
        print("1️⃣  Revoke 旧的 Celery 任务...")
        celery_app.control.revoke(old_celery_task_id, terminate=False)
        print(f"   ✅ 已 revoke: {old_celery_task_id}")
    else:
        print("1️⃣  未提供旧 Celery ID，跳过 revoke 步骤")

    # 第二步：提交新的 generate_all_content_task
    print("\n2️⃣  提交新的内容生成任务...")
    new_celery_result = await asyncio.to_thread(
        generate_all_content_task.apply_async,
        kwargs={
            "roadmap_id": roadmap_id,
            "task_id": task_id,
            "user_id": user_id,
        },
    )
    new_celery_id = new_celery_result.id
    print(f"   ✅ 新任务已入队，Celery ID: {new_celery_id}")

    # 第三步：更新 DB 中的 content_generation_celery_id
    print("\n3️⃣  更新数据库记录...")
    async with get_celery_session() as session:
        task_crud = get_task_crud()
        await task_crud.update_content_generation_celery_id(
            session=session,
            task_id=task_id,
            celery_id=new_celery_id,
        )
    print(f"   ✅ content_generation_celery_id 已更新为: {new_celery_id}")

    print("\n✅ 恢复完成！请在 content worker 日志中观察任务执行情况")
    print(f"   监控关键词: task_id={task_id}")


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    task_id = sys.argv[1]
    roadmap_id = sys.argv[2]
    user_id = sys.argv[3]
    old_celery_task_id = sys.argv[4] if len(sys.argv) >= 5 else None

    asyncio.run(recover(task_id, roadmap_id, user_id, old_celery_task_id))


if __name__ == "__main__":
    main()
