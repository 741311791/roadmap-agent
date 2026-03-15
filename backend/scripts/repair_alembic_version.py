"""
修复 Alembic 版本表指向丢失 revision 的问题。

适用场景：
1. `alembic_version` 中记录的 revision 不存在于当前仓库
2. 实际数据库 schema 已经具备目标 revision 所需结构
3. 需要恢复 `alembic current / upgrade head` 的可用性

用法：
    uv run python scripts/repair_alembic_version.py
    uv run python scripts/repair_alembic_version.py --apply
    uv run python scripts/repair_alembic_version.py --target-revision 20260315_home_perf_idx --apply
"""

import argparse
import asyncio
import os
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
from sqlalchemy import text

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import async_session_maker


def get_alembic_script_directory() -> ScriptDirectory:
    """加载 Alembic 脚本目录。"""
    alembic_ini_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "alembic.ini")
    alembic_config = Config(alembic_ini_path)
    return ScriptDirectory.from_config(alembic_config)


async def get_current_db_revision() -> str | None:
    """读取数据库中的当前 Alembic revision。"""
    async with async_session_maker() as session:
        result = await session.execute(text("SELECT version_num FROM alembic_version"))
        row = result.first()
        return row[0] if row else None


async def set_db_revision(target_revision: str) -> None:
    """直接更新数据库中的 Alembic revision。"""
    async with async_session_maker.begin() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM alembic_version"))
        has_row = int(result.scalar() or 0) > 0

        if has_row:
            await session.execute(
                text("UPDATE alembic_version SET version_num = :version_num"),
                {"version_num": target_revision},
            )
        else:
            await session.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"),
                {"version_num": target_revision},
            )


async def main() -> None:
    """脚本入口。"""
    script_directory = get_alembic_script_directory()
    repo_heads = script_directory.get_heads()
    default_target_revision = repo_heads[0]

    parser = argparse.ArgumentParser(description="修复 Alembic 断链问题")
    parser.add_argument(
        "--target-revision",
        default=default_target_revision,
        help=f"要写入 alembic_version 的目标 revision（默认: {default_target_revision}）",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="真正执行修复；默认仅 dry-run 输出诊断信息",
    )
    args = parser.parse_args()

    current_db_revision = await get_current_db_revision()
    target_revision = args.target_revision

    print("=== Alembic 版本诊断 ===")
    print(f"数据库当前 revision: {current_db_revision}")
    print(f"仓库 heads: {repo_heads}")
    print(f"目标 revision: {target_revision}")

    target_script = script_directory.get_revision(target_revision)
    if target_script is None:
        print("❌ 目标 revision 不存在于当前仓库，请检查 --target-revision")
        sys.exit(1)

    current_script = None
    if current_db_revision:
        try:
            current_script = script_directory.get_revision(current_db_revision)
        except CommandError:
            current_script = None

    if current_script is None and current_db_revision is not None:
        print("⚠️ 当前数据库 revision 不存在于仓库，属于断链状态")
    elif current_script is not None:
        print("✅ 当前数据库 revision 在仓库中可解析")

    if current_db_revision == target_revision:
        print("✅ 数据库 revision 已经是目标值，无需修复")
        return

    if not args.apply:
        print("ℹ️ 当前为 dry-run。确认 schema 已对齐后，使用 --apply 执行修复。")
        return

    await set_db_revision(target_revision)
    print("✅ 已更新 alembic_version")
    print(f"   新 revision: {target_revision}")


if __name__ == "__main__":
    asyncio.run(main())
