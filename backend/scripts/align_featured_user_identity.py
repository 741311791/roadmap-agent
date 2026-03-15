"""
对齐 featured/admin 固定身份脚本。

用途：
1. 检查 `admin@example.com` 当前 user_id 是否等于固定 `FEATURED_USER_ID`
2. 若不一致，可将管理员账号与关键业务表迁移到固定 user_id

用法：
    uv run python scripts/align_featured_user_identity.py
    uv run python scripts/align_featured_user_identity.py --apply
    uv run python scripts/align_featured_user_identity.py --email admin@example.com --target-user-id 04005faa-fb45-47dd-a83c-969a25a77046 --apply
"""

import argparse
import asyncio
import os
import sys
from typing import Sequence

from sqlalchemy import text

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import settings
from app.db.session import async_session_maker


PRIMARY_SYNC_TABLES: Sequence[str] = (
    "roadmap_metadata",
    "roadmap_tasks",
    "user_profiles",
)

SECONDARY_CHECK_TABLES: Sequence[str] = (
    "concept_progress",
    "quiz_attempts",
    "human_review_feedbacks",
    "chat_sessions",
    "learning_notes",
)


async def get_row_count(session, table_name: str, user_id: str) -> int:
    """统计指定表中某个 user_id 的记录数。"""
    result = await session.execute(
        text(f"SELECT COUNT(*) FROM {table_name} WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    return int(result.scalar() or 0)


async def align_featured_user_identity(
    email: str,
    target_user_id: str,
    apply_changes: bool,
    include_secondary_tables: bool,
) -> bool:
    """
    对齐 featured/admin 固定身份。

    Args:
        email: 管理员邮箱
        target_user_id: 目标固定 user_id
        apply_changes: 是否真正执行迁移

    Returns:
        是否执行成功
    """
    async with async_session_maker.begin() as session:
        email_result = await session.execute(
            text(
                """
                SELECT id, email, username
                FROM users
                WHERE email = :email
                """
            ),
            {"email": email},
        )
        existing_admin = email_result.first()

        if not existing_admin:
            print(f"❌ 未找到管理员账号：{email}")
            return False

        current_user_id = existing_admin.id
        print("=== Featured/Admin 身份检查 ===")
        print(f"Email: {email}")
        print(f"当前 User ID: {current_user_id}")
        print(f"目标 User ID: {target_user_id}")

        target_result = await session.execute(
            text(
                """
                SELECT id, email
                FROM users
                WHERE id = :user_id
                """
            ),
            {"user_id": target_user_id},
        )
        target_user = target_result.first()

        if current_user_id == target_user_id:
            print("✅ 管理员账号已使用固定 FEATURED_USER_ID，无需迁移")
            return True

        if target_user and target_user.email != email:
            print("❌ 目标 FEATURED_USER_ID 已被其它账号占用：")
            print(f"   User ID: {target_user.id}")
            print(f"   Email: {target_user.email}")
            return False

        print("\n=== 主表影响范围 ===")
        for table_name in PRIMARY_SYNC_TABLES:
            count = await get_row_count(session, table_name, current_user_id)
            print(f"{table_name}: {count}")

        print("\n=== 次级表检查范围（P2 补充清理）===")
        for table_name in SECONDARY_CHECK_TABLES:
            count = await get_row_count(session, table_name, current_user_id)
            print(f"{table_name}: {count}")

        if not apply_changes:
            print("\nℹ️ 当前为 dry-run。确认无误后使用 --apply 执行迁移。")
            return True

        print("\n=== 开始执行迁移 ===")
        for table_name in PRIMARY_SYNC_TABLES:
            await session.execute(
                text(f"UPDATE {table_name} SET user_id = :target_user_id WHERE user_id = :current_user_id"),
                {
                    "target_user_id": target_user_id,
                    "current_user_id": current_user_id,
                },
            )
            print(f"已更新 {table_name}.user_id")

        if include_secondary_tables:
            print("\n=== 同步清理次级表 ===")
            for table_name in SECONDARY_CHECK_TABLES:
                await session.execute(
                    text(f"UPDATE {table_name} SET user_id = :target_user_id WHERE user_id = :current_user_id"),
                    {
                        "target_user_id": target_user_id,
                        "current_user_id": current_user_id,
                    },
                )
                print(f"已更新 {table_name}.user_id")

        await session.execute(
            text(
                """
                UPDATE users
                SET id = :target_user_id
                WHERE email = :email
                """
            ),
            {
                "target_user_id": target_user_id,
                "email": email,
            },
        )
        print("已更新 users.id")

        print("\n✅ 迁移已完成")
        print("⚠️ 请让管理员重新登录，以避免旧 JWT 中缓存旧 user_id")
        return True


async def main() -> None:
    """脚本入口。"""
    parser = argparse.ArgumentParser(description="对齐 featured/admin 固定身份")
    parser.add_argument(
        "--email",
        default=settings.FEATURED_USER_EMAIL,
        help=f"管理员邮箱（默认: {settings.FEATURED_USER_EMAIL}）",
    )
    parser.add_argument(
        "--target-user-id",
        default=settings.FEATURED_USER_ID,
        help=f"目标固定 FEATURED_USER_ID（默认: {settings.FEATURED_USER_ID}）",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="真正执行迁移；默认仅 dry-run 检查",
    )
    parser.add_argument(
        "--include-secondary",
        action="store_true",
        help="迁移时一并清理 concept_progress、quiz_attempts、chat_sessions 等次级表",
    )

    args = parser.parse_args()
    success = await align_featured_user_identity(
        email=args.email,
        target_user_id=args.target_user_id,
        apply_changes=args.apply,
        include_secondary_tables=args.include_secondary,
    )

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
