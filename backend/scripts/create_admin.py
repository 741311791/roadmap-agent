#!/usr/bin/env python
"""
创建超级管理员账号

使用方法:
    uv run python scripts/create_admin.py
"""
import asyncio
import sys
from getpass import getpass
from app.core.auth.user_manager import get_user_manager
from app.core.auth.schemas import UserCreate
from app.core.auth.backend import get_user_db
from app.db.session import AsyncSessionLocal
import structlog

logger = structlog.get_logger()


async def create_admin(email: str, username: str, password: str):
    """
    创建超级管理员账号
    
    Args:
        email: 管理员邮箱
        username: 管理员用户名
        password: 管理员密码
    """
    try:
        async with AsyncSessionLocal() as session:
            # 获取用户数据库适配器
            user_db_gen = get_user_db(session)
            user_db = await anext(user_db_gen)
            
            # 获取用户管理器
            user_manager_gen = get_user_manager(user_db)
            user_manager = await anext(user_manager_gen)
            
            # 检查用户是否已存在
            existing_user = await user_db.get_by_email(email)
            if existing_user:
                print(f"❌ 用户已存在: {email}")
                return False
            
            # 创建超级管理员
            admin = await user_manager.create(
                UserCreate(
                    email=email,
                    username=username,
                    password=password,
                    is_superuser=True,
                    is_verified=True,
                )
            )
            
            print(f"\n✅ 超级管理员创建成功！")
            print(f"   邮箱: {admin.email}")
            print(f"   用户名: {admin.username}")
            print(f"   ID: {admin.id}")
            print(f"\n请使用此邮箱和密码登录系统。")
            
            return True
            
    except Exception as e:
        print(f"\n❌ 创建失败: {str(e)}")
        logger.exception("create_admin_failed")
        return False


async def main():
    """主函数"""
    print("=" * 60)
    print("创建超级管理员账号")
    print("=" * 60)
    print()
    
    # 获取管理员信息
    email = input("请输入管理员邮箱: ").strip()
    if not email:
        print("❌ 邮箱不能为空")
        sys.exit(1)
    
    username = input("请输入用户名 (默认: admin): ").strip() or "admin"
    
    password = getpass("请输入密码: ").strip()
    if not password:
        print("❌ 密码不能为空")
        sys.exit(1)
    
    password_confirm = getpass("请再次输入密码: ").strip()
    if password != password_confirm:
        print("❌ 两次输入的密码不一致")
        sys.exit(1)
    
    print()
    print("正在创建管理员账号...")
    
    # 创建管理员
    success = await create_admin(email, username, password)
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

