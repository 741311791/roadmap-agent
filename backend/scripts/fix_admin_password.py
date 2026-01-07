"""
修复管理员密码哈希

问题：旧版 create_admin_user.py 使用 bcrypt 直接哈希，与 FastAPI Users 不兼容
解决：使用 passlib 重新哈希密码

用法：
    uv run python scripts/fix_admin_password.py --email admin@example.com --password admin123
"""
import asyncio
import argparse
from sqlalchemy import text
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal
from passlib.context import CryptContext

# ✅ 使用与 FastAPI Users 相同的密码哈希配置
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def fix_admin_password(email: str, password: str):
    """
    更新管理员密码哈希
    
    Args:
        email: 管理员邮箱
        password: 新密码（明文）
    """
    async with AsyncSessionLocal() as session:
        # 检查用户是否存在
        result = await session.execute(
            text("SELECT id, email, username, is_superuser FROM users WHERE email = :email"),
            {"email": email}
        )
        user = result.first()
        
        if not user:
            print(f"❌ 用户不存在：{email}")
            return False
        
        print(f"找到用户：")
        print(f"  ID: {user.id}")
        print(f"  Email: {user.email}")
        print(f"  Username: {user.username}")
        print(f"  Is Superuser: {user.is_superuser}")
        print()
        
        # ✅ 使用 passlib 哈希密码（与 FastAPI Users 完全兼容）
        hashed_password = pwd_context.hash(password)
        
        print(f"生成新密码哈希：{hashed_password[:50]}...")
        print()
        
        # 更新密码
        await session.execute(
            text("""
                UPDATE users 
                SET hashed_password = :hashed_password
                WHERE email = :email
            """),
            {
                "email": email,
                "hashed_password": hashed_password,
            }
        )
        await session.commit()
        
        print("✅ 密码更新成功！")
        print(f"   Email: {email}")
        print(f"   新密码: {password}")
        print()
        print("现在可以使用新密码登录了。")
        
        return True


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="修复管理员密码哈希")
    parser.add_argument(
        "--email",
        required=True,
        help="管理员邮箱"
    )
    parser.add_argument(
        "--password",
        required=True,
        help="新密码（明文）"
    )
    
    args = parser.parse_args()
    
    success = await fix_admin_password(
        email=args.email,
        password=args.password,
    )
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

