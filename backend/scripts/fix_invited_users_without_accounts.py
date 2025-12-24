"""
修复已发送邀请但未创建账号的用户

由于之前的 batch_send_invites 逻辑问题，部分用户收到邮件但账号未创建。
此脚本会找到这些用户并为他们创建账号。

运行方式：
    cd backend
    uv run python scripts/fix_invited_users_without_accounts.py
"""
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_context
from app.models.database import User, WaitlistEmail
from app.core.auth.user_manager import UserManager
from app.core.auth.schemas import UserCreate
from app.core.auth.deps import get_user_db, get_user_manager
from app.services.email_service import get_email_service


async def fix_invited_users():
    """修复已发送邀请但未创建账号的用户"""
    
    async with get_db_context() as db:
        # 查找所有已发送邀请的 waitlist 记录
        result = await db.execute(
            select(WaitlistEmail).where(WaitlistEmail.invited == True)
        )
        invited_waitlist = result.scalars().all()
        
        print(f"找到 {len(invited_waitlist)} 条已发送邀请的记录")
        
        fixed_count = 0
        skipped_count = 0
        failed_count = 0
        
        for entry in invited_waitlist:
            email = entry.email.lower().strip()
            
            # 检查用户是否已存在
            user_result = await db.execute(
                select(User).where(User.email == email)
            )
            existing_user = user_result.scalar_one_or_none()
            
            if existing_user:
                print(f"✓ {email} - 用户账号已存在，跳过")
                skipped_count += 1
                continue
            
            # 检查是否有必要的信息
            if not entry.password or not entry.username or not entry.expires_at:
                print(f"✗ {email} - 缺少必要信息（密码/用户名/过期时间），跳过")
                failed_count += 1
                continue
            
            # 创建用户账号
            try:
                # 这里需要手动创建 UserManager 实例
                # 由于我们在脚本中，无法直接使用依赖注入
                from app.core.auth.database import get_user_db_context
                from fastapi_users.password import PasswordHelper
                from app.core.auth.user_manager import UserManager
                
                async with get_user_db_context(db) as user_db:
                    user_manager = UserManager(user_db)
                    
                    user_create = UserCreate(
                        email=email,
                        username=entry.username,
                        password=entry.password,
                    )
                    
                    new_user = await user_manager.create(user_create)
                    new_user.password_expires_at = entry.expires_at
                    await db.commit()
                    
                    print(f"✓ {email} - 用户账号已创建（ID: {new_user.id}）")
                    fixed_count += 1
                    
            except Exception as e:
                print(f"✗ {email} - 创建失败: {str(e)}")
                failed_count += 1
                await db.rollback()
        
        print("\n" + "="*60)
        print(f"修复完成:")
        print(f"  - 成功创建: {fixed_count}")
        print(f"  - 已存在跳过: {skipped_count}")
        print(f"  - 失败: {failed_count}")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(fix_invited_users())

