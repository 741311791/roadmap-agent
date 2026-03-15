#!/usr/bin/env python3
"""
修复 roadmap_tasks.completed_at 的 UTC 裸值污染问题。

问题背景：
    `roadmap_tasks` 的时间字段约定为“北京时间且不带时区”。
    少数内容生成链路曾错误写入 `datetime.utcnow()`，导致数据库保存为
    无时区的 UTC 时间，最终表现为 `completed_at` 比 `created_at` 早约 8 小时。

安全策略：
    1. 默认 dry-run，只展示将被修复的记录，不执行写入。
    2. 仅修复终态任务。
    3. 仅修复 `completed_at < created_at`，且时间差落在 7~9 小时之间的记录。
    4. 默认只覆盖已确认受影响的任务类型。

使用方法：
    cd backend
    uv run python scripts/fix_roadmap_task_completed_at_timezone.py
    uv run python scripts/fix_roadmap_task_completed_at_timezone.py --apply
"""
import argparse
import asyncio
import sys
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import async_session_maker
from app.models.database import RoadmapTask

DEFAULT_TASK_TYPES = (
    "creation",
    "regenerate_tutorial",
    "regenerate_resources",
    "regenerate_quiz",
)
TERMINAL_STATUSES = ("completed", "failed", "partial_failure")


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数。

    Returns:
        解析后的参数对象。
    """
    parser = argparse.ArgumentParser(
        description="修复 roadmap_tasks.completed_at 的 8 小时时区偏差",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="执行实际修复。默认仅预览。",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=8,
        help="为异常 completed_at 增加的小时数，默认 8。",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=20,
        help="预览时最多展示多少条样本，默认 20。",
    )
    return parser.parse_args()


def is_suspicious_timezone_row(task: RoadmapTask) -> bool:
    """
    判断任务是否符合“UTC 裸值污染”特征。

    Args:
        task: 任务记录。

    Returns:
        是否为疑似受污染记录。
    """
    if (
        task.task_type not in DEFAULT_TASK_TYPES
        or task.status not in TERMINAL_STATUSES
        or task.created_at is None
        or task.completed_at is None
    ):
        return False

    delta_seconds = (task.completed_at - task.created_at).total_seconds()

    # 仅修复“完成时间早于创建时间”且偏差接近 8 小时的记录，避免误改其他异常数据。
    return -9 * 3600 <= delta_seconds <= -7 * 3600


async def load_candidate_tasks() -> list[RoadmapTask]:
    """
    加载疑似受污染的任务记录。

    Returns:
        候选任务列表。
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(RoadmapTask).where(
                RoadmapTask.task_type.in_(DEFAULT_TASK_TYPES),
                RoadmapTask.status.in_(TERMINAL_STATUSES),
                RoadmapTask.created_at.is_not(None),
                RoadmapTask.completed_at.is_not(None),
                RoadmapTask.completed_at < RoadmapTask.created_at,
            )
        )
        tasks = list(result.scalars().all())

    return [task for task in tasks if is_suspicious_timezone_row(task)]


def print_candidates(tasks: list[RoadmapTask], sample_limit: int) -> None:
    """
    打印候选记录预览。

    Args:
        tasks: 候选任务列表。
        sample_limit: 样本展示上限。
    """
    print("\n=== 候选记录概览 ===")
    print(f"命中数量：{len(tasks)}")
    print(f"任务类型范围：{', '.join(DEFAULT_TASK_TYPES)}")
    print(f"状态范围：{', '.join(TERMINAL_STATUSES)}")

    if not tasks:
        print("未发现需要修复的记录。")
        return

    print("\n=== 样本预览 ===")
    for task in tasks[:sample_limit]:
        delta_seconds = int((task.completed_at - task.created_at).total_seconds())
        print(
            f"- task_id={task.task_id} | task_type={task.task_type} | "
            f"status={task.status} | created_at={task.created_at} | "
            f"completed_at={task.completed_at} | delta_seconds={delta_seconds}"
        )


async def apply_fix(tasks: list[RoadmapTask], hours: int) -> int:
    """
    执行修复，将异常 completed_at 向后平移指定小时数。

    Args:
        tasks: 待修复任务列表。
        hours: 平移小时数。

    Returns:
        实际修复数量。
    """
    if not tasks:
        return 0

    task_ids = [task.task_id for task in tasks]
    fixed_count = 0

    async with async_session_maker.begin() as session:
        result = await session.execute(
            select(RoadmapTask).where(RoadmapTask.task_id.in_(task_ids))
        )
        db_tasks = list(result.scalars().all())

        for task in db_tasks:
            if not is_suspicious_timezone_row(task):
                continue

            task.completed_at = task.completed_at + timedelta(hours=hours)
            fixed_count += 1

    return fixed_count


async def main() -> int:
    """
    脚本主入口。

    Returns:
        退出码。0 表示成功，1 表示失败。
    """
    args = parse_args()
    tasks = await load_candidate_tasks()

    print_candidates(tasks, sample_limit=args.sample_limit)

    if not args.apply:
        print("\n当前为 dry-run 模式，未执行任何数据库写入。")
        print("如需真正修复，请追加 `--apply`。")
        return 0

    fixed_count = await apply_fix(tasks, hours=args.hours)
    print(f"\n已修复 {fixed_count} 条记录。")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
