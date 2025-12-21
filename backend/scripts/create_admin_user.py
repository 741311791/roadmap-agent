"""
创建管理员用户脚本

用法：
    uv run python scripts/create_admin_user.py
    
或者自定义参数：
    uv run python scripts/create_admin_user.py --email admin@example.com --password admin123
    uv run python scripts/create_admin_user.py --email admin@example.com --password admin123 --user-id 04005faa-fb45-47dd-a83c-969a25a77046 --username admin
"""
import asyncio
import argparse
from sqlalchemy import text
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal
from datetime import datetime, timezone, timedelta
import uuid
import bcrypt


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
    async with AsyncSessionLocal() as session:
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
        
        # 哈希密码（使用 bcrypt，与 FastAPI Users 兼容）
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
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
                "id": user_id,
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
        print(f"   User ID: {user_id}")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   密码: {password}")
        print(f"   超级管理员: 是")
        print(f"   创建时间: {created_at}")
        
        return True


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="创建管理员用户")
    parser.add_argument(
        "--email",
        default="admin@example.com",
        help="管理员邮箱（默认: admin@example.com）"
    )
    parser.add_argument(
        "--password",
        default="admin123",
        help="管理员密码（默认: admin123）"
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="用户 ID（可选，不提供则自动生成）"
    )
    parser.add_argument(
        "--username",
        default=None,
        help="用户名（可选，默认为 email 的本地部分）"
    )
    
    args = parser.parse_args()
    
    success = await create_admin_user(
        email=args.email,
        password=args.password,
        user_id=args.user_id,
        username=args.username,
    )
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

