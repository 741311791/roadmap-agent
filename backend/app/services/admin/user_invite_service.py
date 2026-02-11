"""
用户邀请服务

负责处理:
- 用户邀请逻辑
- Waitlist管理
- 批量邀请处理
"""
import secrets
import string
from datetime import timedelta
from typing import List, Dict, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import structlog

from app.models.database import User, WaitlistEmail, beijing_now
from app.core.auth.user_manager import UserManager
from app.core.auth.schemas import UserCreate
from app.services.shared.email_service import EmailService

logger = structlog.get_logger()


def generate_random_password(length: int = 16) -> str:
    """
    生成随机密码
    
    Args:
        length: 密码长度
        
    Returns:
        随机密码字符串
    """
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


class UserInviteService:
    """用户邀请业务逻辑"""
    
    async def invite_single_user(
        self,
        session: AsyncSession,
        email: str,
        password_validity_days: int,
        user_manager: UserManager,
        email_service: Optional[EmailService] = None,
        send_email: bool = True,
    ) -> Dict:
        """
        邀请单个用户
        
        Args:
            session: 数据库会话
            email: 用户邮箱
            password_validity_days: 密码有效天数
            user_manager: 用户管理器
            email_service: 邮件服务
            send_email: 是否发送邮件
            
        Returns:
            邀请结果字典
            
        Raises:
            ValueError: 用户已存在
        """
        email = email.lower().strip()
        
        # 检查用户是否已存在
        result = await session.execute(
            select(User).where(User.email == email)
        )
        if result.scalars().first():
            raise ValueError(f"User with email {email} already exists")
        
        # 生成临时密码和用户名
        temp_password = generate_random_password()
        username = email.split('@')[0]
        expires_at = beijing_now() + timedelta(days=password_validity_days)
        
        # 创建用户
        user_create = UserCreate(
            email=email,
            username=username,
            password=temp_password,
        )
        new_user = await user_manager.create(user_create)
        new_user.password_expires_at = expires_at
        await session.flush()
        
        # 更新Waitlist记录
        waitlist_result = await session.execute(
            select(WaitlistEmail).where(WaitlistEmail.email == email)
        )
        waitlist_entry = waitlist_result.scalars().first()
        if waitlist_entry:
            waitlist_entry.invited = True
            waitlist_entry.invited_at = beijing_now()
            await session.flush()
        
        logger.info(
            "user_invited",
            user_id=new_user.id,
            email=email,
            expires_at=expires_at.isoformat(),
        )
        
        # 发送邮件
        email_sent = False
        if send_email and email_service:
            email_sent = await email_service.send_invite_email(
                to_email=email,
                temp_password=temp_password,
                expires_at=expires_at,
                username=username,
            )
        
        message = f"User created. Password expires on {expires_at.strftime('%Y-%m-%d %H:%M')} (Beijing Time)."
        if send_email:
            message += " Invitation email sent." if email_sent else " Failed to send invitation email."
        
        return {
            "success": True,
            "email": email,
            "username": username,
            "temp_password": temp_password,
            "expires_at": expires_at.isoformat(),
            "message": message,
        }
    
    async def get_waitlist(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        pending_only: bool = False,
    ) -> Dict:
        """
        获取Waitlist列表
        
        Args:
            session: 数据库会话
            limit: 分页大小
            offset: 偏移量
            pending_only: 是否只显示未邀请
            
        Returns:
            Waitlist数据和统计信息
        """
        # 构建查询
        query = select(WaitlistEmail)
        if pending_only:
            query = query.where(WaitlistEmail.invited == False)
        query = query.order_by(WaitlistEmail.created_at.desc()).limit(limit).offset(offset)
        
        result = await session.execute(query)
        users = list(result.scalars().all())
        
        # 统计信息
        total_result = await session.execute(
            select(func.count()).select_from(WaitlistEmail)
        )
        total = total_result.scalar() or 0
        
        invited_result = await session.execute(
            select(func.count()).select_from(WaitlistEmail).where(WaitlistEmail.invited == True)
        )
        invited = invited_result.scalar() or 0
        
        return {
            "users": users,
            "total": total,
            "pending": total - invited,
            "invited": invited,
        }
    
    async def get_waitlist_invites(
        self,
        session: AsyncSession,
        limit: int = 100,
        offset: int = 0,
        status: str = "all",
    ) -> Dict:
        """
        获取Waitlist邀请列表（含凭证）
        
        Args:
            session: 数据库会话
            limit: 分页大小
            offset: 偏移量
            status: 过滤状态 (all/pending/invited)
            
        Returns:
            邀请列表和统计信息
        """
        # 构建查询
        query = select(WaitlistEmail)
        if status == "pending":
            query = query.where(WaitlistEmail.invited == False)
        elif status == "invited":
            query = query.where(WaitlistEmail.invited == True)
        
        query = query.order_by(WaitlistEmail.created_at.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        items = list(result.scalars().all())
        
        # 统计信息
        total_result = await session.execute(
            select(func.count()).select_from(WaitlistEmail)
        )
        total = total_result.scalar() or 0
        
        invited_result = await session.execute(
            select(func.count()).select_from(WaitlistEmail).where(WaitlistEmail.invited == True)
        )
        invited = invited_result.scalar() or 0
        
        return {
            "items": items,
            "total": total,
            "pending": total - invited,
            "invited": invited,
        }
    
    async def batch_send_invites(
        self,
        session: AsyncSession,
        emails: List[str],
        password_validity_days: int,
        admin_user_id: str,
        user_manager: UserManager,
        email_service: EmailService,
    ) -> Tuple[int, List[Dict]]:
        """
        批量发送邀请
        
        采用"一次读取，批量处理，部分提交"策略。
        
        Args:
            session: 数据库会话
            emails: 邮箱列表
            password_validity_days: 密码有效天数
            admin_user_id: 管理员ID
            user_manager: 用户管理器
            email_service: 邮件服务
            
        Returns:
            (成功数量, 错误列表)
        """
        # 标准化邮箱
        normalized_emails = [email.lower().strip() for email in emails]
        
        # Step 1: 批量读取waitlist记录
        waitlist_result = await session.execute(
            select(WaitlistEmail).where(WaitlistEmail.email.in_(normalized_emails))
        )
        waitlist_map = {entry.email: entry for entry in waitlist_result.scalars().all()}
        
        # Step 2: 批量读取已存在用户
        existing_users_result = await session.execute(
            select(User.email).where(User.email.in_(normalized_emails))
        )
        existing_users_set = set(existing_users_result.scalars().all())
        
        # Step 3: 预处理，区分可处理和不可处理的邮箱
        errors = []
        emails_to_process = []
        
        for email in normalized_emails:
            waitlist_entry = waitlist_map.get(email)
            
            if not waitlist_entry:
                errors.append({"email": email, "error": "Email not found in waitlist"})
                continue
            
            if waitlist_entry.invited:
                errors.append({"email": email, "error": "Invitation already sent"})
                continue
            
            if email in existing_users_set:
                errors.append({"email": email, "error": "User account already exists"})
                continue
            
            emails_to_process.append((email, waitlist_entry))
        
        # Step 4: 逐个处理（因为邮件发送是外部副作用）
        success_count = 0
        
        for email, waitlist_entry in emails_to_process:
            try:
                username = email.split('@')[0]
                temp_password = generate_random_password()
                expires_at = beijing_now() + timedelta(days=password_validity_days)
                
                # 创建用户
                user_create = UserCreate(
                    email=email,
                    username=username,
                    password=temp_password,
                )
                new_user = await user_manager.create(user_create)
                new_user.password_expires_at = expires_at
                
                # 发送邮件
                email_sent = await email_service.send_invite_email(
                    to_email=email,
                    temp_password=temp_password,
                    expires_at=expires_at,
                    username=username,
                )
                
                if email_sent:
                    # 更新waitlist记录
                    waitlist_entry.username = username
                    waitlist_entry.password = temp_password
                    waitlist_entry.expires_at = expires_at
                    waitlist_entry.invited = True
                    waitlist_entry.invited_at = beijing_now()
                    waitlist_entry.sent_content = {
                        "username": username,
                        "expires_at": expires_at.isoformat(),
                        "sent_at": beijing_now().isoformat(),
                        "sent_by": admin_user_id,
                    }
                    success_count += 1
                    
                    logger.info(
                        "batch_invite_success",
                        admin_id=admin_user_id,
                        email=email,
                        user_id=new_user.id,
                    )
                else:
                    # 邮件发送失败，回滚
                    await session.rollback()
                    errors.append({
                        "email": email,
                        "error": "Failed to send email, user account not created"
                    })
                    logger.warning("batch_invite_email_failed", email=email)
                    
            except Exception as e:
                await session.rollback()
                errors.append({"email": email, "error": str(e)})
                logger.error("batch_invite_error", email=email, error=str(e))
        
        logger.info(
            "batch_invites_completed",
            admin_id=admin_user_id,
            success=success_count,
            failed=len(errors),
        )
        
        return success_count, errors

