#!/usr/bin/env python3
"""
清空 PostgreSQL 数据库连接

功能：
    1. 查看当前所有数据库连接状态
    2. 终止所有空闲（idle）连接
    3. 终止所有非当前连接（可选，危险操作）

使用方法：
    cd backend
    uv run python scripts/clear_db_connections.py           # 仅终止 idle 连接
    uv run python scripts/clear_db_connections.py --all     # 终止所有连接（谨慎使用）
    uv run python scripts/clear_db_connections.py --status  # 仅查看连接状态

适用场景：
    - 连接池耗尽，无法建立新连接
    - 大量 idle 连接堆积影响性能
    - 开发调试时需要重置连接状态
"""
import asyncio
import sys
import argparse
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
import structlog

from app.config.settings import settings

logger = structlog.get_logger()

# ============================================================
# 查询当前连接状态
# ============================================================
async def show_connections(engine) -> list[dict]:
    """
    查询并展示当前数据库连接状态

    Args:
        engine: SQLAlchemy 异步引擎

    Returns:
        连接信息列表
    """
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT
                pid,
                usename          AS username,
                application_name,
                client_addr,
                state,
                wait_event_type,
                wait_event,
                query_start,
                state_change,
                EXTRACT(EPOCH FROM (NOW() - state_change))::INT AS idle_seconds,
                LEFT(query, 80)  AS query_preview
            FROM pg_stat_activity
            WHERE datname = current_database()
              AND pid <> pg_backend_pid()
            ORDER BY state, idle_seconds DESC NULLS LAST
        """))
        rows = result.mappings().all()

    connections = [dict(row) for row in rows]

    # 统计各状态数量
    state_counts: dict[str, int] = {}
    for conn_info in connections:
        state = conn_info.get("state") or "unknown"
        state_counts[state] = state_counts.get(state, 0) + 1

    print("\n" + "=" * 70)
    print(f"📊 数据库连接状态  [库: {settings.POSTGRES_DB}]")
    print("=" * 70)
    print(f"总连接数（不含当前脚本连接）: {len(connections)}")

    for state, count in sorted(state_counts.items()):
        icon = "🟢" if state == "active" else "🟡" if state == "idle" else "🔴"
        print(f"  {icon} {state}: {count} 个")

    if connections:
        print("\n详细连接列表:")
        print("-" * 70)
        for c in connections:
            idle_str = f"{c['idle_seconds']}s" if c.get('idle_seconds') is not None else "N/A"
            print(
                f"  PID:{c['pid']:<8} "
                f"状态:{str(c['state'] or 'unknown'):<12} "
                f"空闲:{idle_str:<8} "
                f"应用:{str(c['application_name'] or ''):<20} "
                f"用户:{c['username']}"
            )
            if c.get("query_preview"):
                print(f"           SQL: {c['query_preview']}")
    else:
        print("\n  ✅ 当前没有其他数据库连接")

    print("=" * 70)
    return connections


# ============================================================
# 终止空闲连接
# ============================================================
async def terminate_idle_connections(engine, idle_threshold_seconds: int = 0) -> int:
    """
    终止所有空闲（idle）连接

    Args:
        engine: SQLAlchemy 异步引擎
        idle_threshold_seconds: 空闲时间阈值（秒），0 表示终止所有 idle 连接

    Returns:
        终止的连接数量
    """
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT COUNT(*) AS terminated
            FROM (
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND pid <> pg_backend_pid()
                  AND state = 'idle'
                  AND EXTRACT(EPOCH FROM (NOW() - state_change)) >= :threshold
            ) sub
            WHERE pg_terminate_backend = true
        """), {"threshold": idle_threshold_seconds})
        row = result.one()
        terminated = row[0]

    return terminated


# ============================================================
# 终止所有连接（危险操作）
# ============================================================
async def terminate_all_connections(engine) -> int:
    """
    终止当前数据库的所有连接（除当前脚本连接外）

    ⚠️ 警告：此操作会中断所有正在执行的查询，慎用！

    Args:
        engine: SQLAlchemy 异步引擎

    Returns:
        终止的连接数量
    """
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT COUNT(*) AS terminated
            FROM (
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = current_database()
                  AND pid <> pg_backend_pid()
            ) sub
            WHERE pg_terminate_backend = true
        """))
        row = result.one()
        terminated = row[0]

    return terminated


# ============================================================
# 安全确认
# ============================================================
def confirm_action(action_desc: str) -> bool:
    """
    要求用户确认危险操作

    Args:
        action_desc: 操作描述

    Returns:
        用户是否确认
    """
    print(f"\n⚠️  即将执行：{action_desc}")
    print(f"目标数据库: {settings.POSTGRES_DB}  @ {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}")
    response = input("请输入 'YES' 确认继续: ").strip()
    return response == "YES"


# ============================================================
# 主函数
# ============================================================
async def main(show_status_only: bool = False, terminate_all: bool = False):
    """
    主执行函数

    Args:
        show_status_only: 仅展示连接状态，不执行任何终止操作
        terminate_all: 是否终止所有连接（包括 active 状态）
    """
    # 创建一个独立的、轻量级引擎（避免使用应用连接池）
    engine = create_async_engine(
        settings.DATABASE_URL,
        pool_size=1,
        max_overflow=0,
        echo=False,
    )

    try:
        # 第一步：展示当前连接状态
        connections = await show_connections(engine)

        if show_status_only:
            print("\n✅ 仅查看模式，未执行任何操作")
            return

        if not connections:
            print("\n✅ 没有需要清理的连接")
            return

        # 第二步：执行终止操作
        if terminate_all:
            # 终止所有连接（需要用户二次确认）
            if not confirm_action("终止所有数据库连接（包括正在执行的查询）"):
                print("❌ 用户取消操作")
                return

            print("\n⚙️  正在终止所有连接...")
            count = await terminate_all_connections(engine)
            print(f"✅ 已终止 {count} 个连接")

        else:
            # 默认：仅终止 idle 连接
            idle_count = sum(1 for c in connections if c.get("state") == "idle")
            if idle_count == 0:
                print("\n✅ 当前没有 idle 连接需要清理")
                return

            if not confirm_action(f"终止 {idle_count} 个空闲（idle）连接"):
                print("❌ 用户取消操作")
                return

            print("\n⚙️  正在终止 idle 连接...")
            count = await terminate_idle_connections(engine, idle_threshold_seconds=0)
            print(f"✅ 已终止 {count} 个 idle 连接")

        # 第三步：展示操作后的连接状态
        print("\n📊 操作后的连接状态：")
        await show_connections(engine)

    except Exception as e:
        logger.error("clear_db_connections_failed", error=str(e), error_type=type(e).__name__)
        print(f"\n❌ 操作失败: {e}")
        sys.exit(1)

    finally:
        await engine.dispose()


# ============================================================
# 命令行入口
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="清空 PostgreSQL 数据库连接",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  仅查看当前连接状态:
    uv run python scripts/clear_db_connections.py --status

  终止所有 idle 连接（默认行为）:
    uv run python scripts/clear_db_connections.py

  终止所有连接（包括 active，谨慎使用）:
    uv run python scripts/clear_db_connections.py --all
        """,
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="仅展示当前连接状态，不执行终止操作",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="终止所有连接（包括正在执行的查询，危险操作）",
    )
    args = parser.parse_args()

    asyncio.run(main(show_status_only=args.status, terminate_all=args.all))
