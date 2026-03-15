#!/usr/bin/env python3
"""
修复 roadmap_tasks.content_generation_status 的历史错位问题。

问题类型：
    1. creation 任务已进入终态，但 content_generation_status 仍为 processing
    2. regenerate_* 任务已进入终态，但 content_generation_status 仍为 pending/processing

安全策略：
    1. 默认 dry-run，仅展示候选记录。
    2. 仅修复已知受影响的任务类型。
    3. 仅修复明确可推导最终状态的记录。

使用方法：
    cd backend
    uv run python scripts/fix_roadmap_task_content_generation_status.py
    uv run python scripts/fix_roadmap_task_content_generation_status.py --apply
"""
import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import async_session_maker
from app.models.database import RoadmapTask

CREATION_TASK_TYPES = {"creation"}
REGENERATE_TASK_TYPES = {"regenerate_tutorial", "regenerate_resources", "regenerate_quiz"}
TERMINAL_TASK_STATUSES = {"completed", "failed", "partial_failure", "cancelled"}


def parse_args() -> argparse.Namespace:
    """
    解析命令行参数。

    Returns:
        命令行参数对象。
    """
    parser = argparse.ArgumentParser(
        description="修复 roadmap_tasks.content_generation_status 历史错位",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="执行实际修复。默认仅预览。",
    )
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=30,
        help="预览时最多展示多少条样本，默认 30。",
    )
    return parser.parse_args()


def infer_target_content_status(task: RoadmapTask) -> str | None:
    """
    推导任务应当回写的内容生成状态。

    Args:
        task: 任务记录。

    Returns:
        目标 content_generation_status；若不应修复则返回 None。
    """
    if task.task_type in CREATION_TASK_TYPES:
        if task.status in {"completed", "failed", "partial_failure"} and task.content_generation_status == "processing":
            return task.status
        if task.status == "cancelled" and task.content_generation_status == "processing":
            return "failed"
        return None

    if task.task_type in REGENERATE_TASK_TYPES:
        if task.status in {"completed", "failed"} and task.content_generation_status in {"pending", "processing"}:
            return task.status
        return None

    return None


async def load_candidates() -> list[tuple[RoadmapTask, str]]:
    """
    加载候选修复记录。

    Returns:
        `(任务记录, 目标状态)` 列表。
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(RoadmapTask).where(
                RoadmapTask.status.in_(TERMINAL_TASK_STATUSES),
                RoadmapTask.task_type.in_(tuple(CREATION_TASK_TYPES | REGENERATE_TASK_TYPES)),
            )
        )
        tasks = list(result.scalars().all())

    candidates: list[tuple[RoadmapTask, str]] = []
    for task in tasks:
        target_status = infer_target_content_status(task)
        if target_status is not None:
            candidates.append((task, target_status))

    return candidates


def print_candidates(candidates: list[tuple[RoadmapTask, str]], sample_limit: int) -> None:
    """
    打印候选修复记录。

    Args:
        candidates: 候选列表。
        sample_limit: 样本上限。
    """
    print("\n=== 候选记录概览 ===")
    print(f"命中数量：{len(candidates)}")

    if not candidates:
        print("未发现需要修复的记录。")
        return

    print("\n=== 样本预览 ===")
    for task, target_status in candidates[:sample_limit]:
        print(
            f"- task_id={task.task_id} | task_type={task.task_type} | "
            f"task_status={task.status} | content_generation_status={task.content_generation_status} "
            f"-> {target_status} | current_step={task.current_step}"
        )


async def apply_fix(candidates: list[tuple[RoadmapTask, str]]) -> int:
    """
    执行数据库修复。

    Args:
        candidates: 候选列表。

    Returns:
        实际修复条数。
    """
    if not candidates:
        return 0

    candidate_map = {task.task_id: target_status for task, target_status in candidates}

    async with async_session_maker.begin() as session:
        result = await session.execute(
            select(RoadmapTask).where(RoadmapTask.task_id.in_(tuple(candidate_map.keys())))
        )
        tasks = list(result.scalars().all())

        fixed_count = 0
        for task in tasks:
            target_status = candidate_map.get(task.task_id)
            if target_status is None:
                continue

            if infer_target_content_status(task) is None:
                continue

            task.content_generation_status = target_status
            fixed_count += 1

    return fixed_count


async def main() -> int:
    """
    脚本主入口。

    Returns:
        退出码。0 表示成功。
    """
    args = parse_args()
    candidates = await load_candidates()
    print_candidates(candidates, sample_limit=args.sample_limit)

    if not args.apply:
        print("\n当前为 dry-run 模式，未执行任何数据库写入。")
        print("如需真正修复，请追加 `--apply`。")
        return 0

    fixed_count = await apply_fix(candidates)
    print(f"\n已修复 {fixed_count} 条记录。")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
