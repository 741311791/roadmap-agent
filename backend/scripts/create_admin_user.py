"""
创建管理员用户脚本

✅ v2.1: 添加创建测试用户功能

用法：
    # 只创建管理员
    uv run python scripts/create_admin_user.py
    
    # 同时创建管理员和测试用户
    uv run python scripts/create_admin_user.py --create-test-user
    
    # 自定义参数
    uv run python scripts/create_admin_user.py --email admin@example.com --password admin123
    uv run python scripts/create_admin_user.py --email admin@example.com --password admin123 --user-id 04005faa-fb45-47dd-a83c-969a25a77046 --username admin --create-test-user

测试用户信息：
    Email: e2e_test_permanent@example.com
    Password: Test123456!
"""
import asyncio
import argparse
from sqlalchemy import text
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import async_session_maker
from app.config.settings import settings
from datetime import datetime, timezone, timedelta
import uuid
from passlib.context import CryptContext

# ✅ 使用与 FastAPI Users 相同的密码哈希配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def create_admin_user(
    email: str,
    password: str,
    user_id: str | None = None,
    username: str | None = None,
):
    """
    创建管理员用户
    
    参数：
        email: 管理员邮箱
        password: 管理员密码（明文）
        user_id: 用户 ID（可选，不提供则自动生成）
        username: 用户名（可选，默认为 email 的本地部分）
    """
    async with async_session_maker.begin() as session:
        # 生成 user_id（如果未提供）
        target_user_id = user_id or settings.FEATURED_USER_ID or str(uuid.uuid4())

        # 检查邮箱是否已存在
        email_result = await session.execute(
            text("SELECT id, email FROM users WHERE email = :email"),
            {"email": email}
        )
        existing_by_email = email_result.first()

        # 检查目标 user_id 是否已被其它账号占用
        id_result = await session.execute(
            text("SELECT id, email FROM users WHERE id = :id"),
            {"id": target_user_id}
        )
        existing_by_id = id_result.first()

        if existing_by_id and existing_by_id.email != email:
            print("❌ 固定管理员 ID 已被其它账号占用：")
            print(f"   User ID: {existing_by_id.id}")
            print(f"   Email: {existing_by_id.email}")
            print("   请先完成管理员身份迁移，再重新执行脚本。")
            return False

        if existing_by_email:
            if existing_by_email.id != target_user_id:
                print("❌ 管理员邮箱已存在，但 user_id 与固定 FEATURED_USER_ID 不一致：")
                print(f"   Email: {existing_by_email.email}")
                print(f"   当前 User ID: {existing_by_email.id}")
                print(f"   目标 User ID: {target_user_id}")
                print("   请先运行管理员身份对齐脚本，再重新执行。")
                return False

            # 说明：
            # Railway 启动时会重复执行该脚本，因此这里改为幂等更新。
            # 仅确保管理员身份和用户名正确，不自动重置密码，避免生产环境误覆盖。
            await session.execute(
                text("""
                    UPDATE users
                    SET
                        username = :username,
                        is_active = TRUE,
                        is_superuser = TRUE,
                        is_verified = TRUE
                    WHERE id = :id
                """),
                {
                    "id": target_user_id,
                    "username": username or email.split("@")[0],
                }
            )
            await session.commit()
            print("✅ 管理员账号已存在，已完成一致性校验")
            print(f"   User ID: {target_user_id}")
            print(f"   Email: {email}")
            return True
        
        # 生成 username（如果未提供）
        if not username:
            username = email.split("@")[0]
        
        # ✅ 哈希密码（使用 passlib，与 FastAPI Users 完全兼容）
        hashed_password = pwd_context.hash(password)
        
        # 获取当前北京时间（无时区）
        utc_now = datetime.now(timezone.utc)
        beijing_time = utc_now + timedelta(hours=8)
        created_at = beijing_time.replace(tzinfo=None)
        
        # 插入管理员账号
        await session.execute(
            text("""
                INSERT INTO users (
                    id, email, username, hashed_password, 
                    is_active, is_superuser, is_verified,
                    password_expires_at, created_at
                ) VALUES (
                    :id, :email, :username, :hashed_password,
                    :is_active, :is_superuser, :is_verified,
                    :password_expires_at, :created_at
                )
            """),
            {
                "id": target_user_id,
                "email": email,
                "username": username,
                "hashed_password": hashed_password,
                "is_active": True,
                "is_superuser": True,
                "is_verified": True,
                "password_expires_at": None,
                "created_at": created_at,
            }
        )
        await session.commit()
        
        print("✅ 管理员账号创建成功！")
        print(f"   User ID: {target_user_id}")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   密码: {password}")
        print(f"   超级管理员: 是")
        print(f"   创建时间: {created_at}")
        
        return True


async def create_test_user(
    email: str,
    password: str,
    user_id: str | None = None,
    username: str | None = None,
):
    """
    创建测试用户（非管理员）
    
    参数：
        email: 测试用户邮箱
        password: 测试用户密码（明文）
        user_id: 用户 ID（可选，不提供则自动生成）
        username: 用户名（可选，默认为 email 的本地部分）
    """
    async with async_session_maker.begin() as session:
        # 检查用户是否已存在
        result = await session.execute(
            text("SELECT id, email FROM users WHERE email = :email"),
            {"email": email}
        )
        existing = result.first()
        
        if existing:
            print(f"❌ 用户已存在：{existing.email} (ID: {existing.id})")
            return False
        
        # 生成 user_id（如果未提供）
        if not user_id:
            user_id = str(uuid.uuid4())
        
        # 生成 username（如果未提供）
        if not username:
            username = email.split("@")[0]
        
        # 哈希密码
        hashed_password = pwd_context.hash(password)
        
        # 获取当前北京时间（无时区）
        utc_now = datetime.now(timezone.utc)
        beijing_time = utc_now + timedelta(hours=8)
        created_at = beijing_time.replace(tzinfo=None)
        
        # 插入测试账号（非管理员）
        await session.execute(
            text("""
                INSERT INTO users (
                    id, email, username, hashed_password, 
                    is_active, is_superuser, is_verified,
                    password_expires_at, created_at
                ) VALUES (
                    :id, :email, :username, :hashed_password,
                    :is_active, :is_superuser, :is_verified,
                    :password_expires_at, :created_at
                )
            """),
            {
                "id": user_id,
                "email": email,
                "username": username,
                "hashed_password": hashed_password,
                "is_active": True,
                "is_superuser": False,  # 非管理员
                "is_verified": True,
                "password_expires_at": None,
                "created_at": created_at,
            }
        )
        await session.commit()
        
        print("✅ 测试账号创建成功！")
        print(f"   User ID: {user_id}")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   密码: {password}")
        print(f"   超级管理员: 否")
        print(f"   创建时间: {created_at}")
        
        return True


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="创建管理员用户和测试用户")
    parser.add_argument(
        "--email",
        default=settings.FEATURED_USER_EMAIL,
        help=f"管理员邮箱（默认: {settings.FEATURED_USER_EMAIL}）"
    )
    parser.add_argument(
        "--password",
        default="admin123",
        help="管理员密码（默认: admin123）"
    )
    parser.add_argument(
        "--user-id",
        default=settings.FEATURED_USER_ID,
        help=f"用户 ID（默认固定为 FEATURED_USER_ID: {settings.FEATURED_USER_ID}）"
    )
    parser.add_argument(
        "--username",
        default=None,
        help="用户名（可选，默认为 email 的本地部分）"
    )
    parser.add_argument(
        "--create-test-user",
        action="store_true",
        help="同时创建测试用户"
    )
    
    args = parser.parse_args()
    
    # 创建管理员用户
    print("\n=== 创建管理员用户 ===")
    success = await create_admin_user(
        email=args.email,
        password=args.password,
        user_id=args.user_id,
        username=args.username,
    )
    
    # 如果指定了创建测试用户，则创建测试用户
    if args.create_test_user:
        print("\n=== 创建测试用户 ===")
        test_success = await create_test_user(
            email="e2e_test_permanent@example.com",
            password="Test123456!",
        )
        if not test_success:
            print("⚠️  测试用户创建失败，但管理员用户已创建")
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

