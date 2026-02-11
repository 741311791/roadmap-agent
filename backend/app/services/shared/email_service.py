"""
邮件服务

使用 Resend 发送邮件，包括邀请邮件、密码重置等。
"""
from datetime import datetime
from typing import Optional
import structlog

from app.config.settings import settings

logger = structlog.get_logger()


class EmailService:
    """
    邮件发送服务
    
    使用 Resend API 发送各类邮件。
    如果未配置 Resend API Key，将以日志形式输出邮件内容（开发模式）。
    """
    
    def __init__(self):
        """初始化邮件服务"""
        self._resend = None
        self._initialized = False
        
        if settings.RESEND_API_KEY:
            try:
                import resend
                resend.api_key = settings.RESEND_API_KEY
                self._resend = resend
                self._initialized = True
                logger.info("email_service_initialized", provider="resend")
            except ImportError:
                logger.warning(
                    "email_service_resend_not_installed",
                    message="resend package not installed, emails will be logged only"
                )
        else:
            logger.warning(
                "email_service_no_api_key",
                message="RESEND_API_KEY not configured, emails will be logged only"
            )
    
    async def send_invite_email(
        self,
        to_email: str,
        temp_password: str,
        expires_at: datetime,
        username: str,
    ) -> bool:
        """
        发送邀请邮件
        
        包含临时登录凭证，用户可以使用这些凭证登录系统。
        
        Args:
            to_email: 收件人邮箱
            temp_password: 临时密码
            expires_at: 密码过期时间
            username: 用户名
            
        Returns:
            是否发送成功
        """
        subject = "Welcome to Fast Learning Beta!"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to Fast Learning</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 20px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 28px;">🎉 Welcome to Fast Learning!</h1>
    </div>
    
    <div style="background: #ffffff; padding: 30px; border: 1px solid #e0e0e0; border-top: none; border-radius: 0 0 12px 12px;">
        <p style="font-size: 16px; margin-bottom: 20px;">
            Hi <strong>{username}</strong>,
        </p>
        
        <p style="font-size: 16px; margin-bottom: 20px;">
            You've been invited to join the Fast Learning beta program! 
            We're excited to have you on board.
        </p>
        
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin: 0 0 15px 0; color: #555;">Your Login Credentials</h3>
            <p style="margin: 5px 0;"><strong>Email:</strong> {to_email}</p>
            <p style="margin: 5px 0;"><strong>Temporary Password:</strong> 
                <code style="background: #e9ecef; padding: 4px 8px; border-radius: 4px; font-family: monospace;">{temp_password}</code>
            </p>
        </div>
        
        <div style="background: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
            <p style="margin: 0; font-size: 14px;">
                ⚠️ <strong>Important:</strong> This password will expire on 
                <strong>{expires_at.strftime('%Y-%m-%d %H:%M')} (Beijing Time)</strong>.
            </p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <a href="{settings.FRONTEND_URL}/login" 
               style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 14px 30px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px;">
                Login Now →
            </a>
        </div>
        
        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
        
        <p style="font-size: 14px; color: #666;">
            If you have any questions, feel free to reply to this email.
        </p>
        
        <p style="font-size: 14px; color: #666;">
            Happy Learning! 🚀<br>
            <strong>The Fast Learning Team</strong>
        </p>
    </div>
    
    <div style="text-align: center; padding: 20px; color: #999; font-size: 12px;">
        <p>© 2024 Fast Learning. All rights reserved.</p>
    </div>
</body>
</html>
        """
        
        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
        )
    
    async def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        expires_in_hours: int = 24,
    ) -> bool:
        """
        发送密码重置邮件
        
        Args:
            to_email: 收件人邮箱
            reset_token: 重置令牌
            expires_in_hours: 令牌有效期（小时）
            
        Returns:
            是否发送成功
        """
        subject = "Reset Your Fast Learning Password"
        
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Reset Password</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h2>Reset Your Password</h2>
    
    <p>We received a request to reset your password. Click the button below to create a new password:</p>
    
    <div style="text-align: center; margin: 30px 0;">
        <a href="{reset_url}" 
           style="display: inline-block; background: #667eea; color: white; padding: 14px 30px; text-decoration: none; border-radius: 8px; font-weight: 600;">
            Reset Password
        </a>
    </div>
    
    <p style="color: #666; font-size: 14px;">
        This link will expire in {expires_in_hours} hours. 
        If you didn't request a password reset, you can safely ignore this email.
    </p>
    
    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
    
    <p style="color: #999; font-size: 12px;">
        © 2024 Fast Learning
    </p>
</body>
</html>
        """
        
        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
        )
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
    ) -> bool:
        """
        内部邮件发送方法
        
        Args:
            to_email: 收件人
            subject: 主题
            html_content: HTML 内容
            text_content: 纯文本内容（可选）
            
        Returns:
            是否成功
        """
        if self._initialized and self._resend:
            try:
                params = {
                    "from": settings.RESEND_FROM_EMAIL,
                    "to": to_email,
                    "subject": subject,
                    "html": html_content,
                }
                
                if text_content:
                    params["text"] = text_content
                
                response = self._resend.Emails.send(params)
                
                logger.info(
                    "email_sent_successfully",
                    to=to_email,
                    subject=subject,
                    response_id=response.get("id") if isinstance(response, dict) else str(response),
                )
                return True
                
            except Exception as e:
                logger.error(
                    "email_send_failed",
                    to=to_email,
                    subject=subject,
                    error=str(e),
                )
                return False
        else:
            # 开发模式：仅记录日志
            logger.info(
                "email_logged_dev_mode",
                to=to_email,
                subject=subject,
                message="Email not actually sent (dev mode or Resend not configured)",
                html_preview=html_content[:500] + "..." if len(html_content) > 500 else html_content,
            )
            return True


# 全局单例
email_service = EmailService()


def get_email_service() -> EmailService:
    """获取邮件服务实例（用于依赖注入）"""
    return email_service

