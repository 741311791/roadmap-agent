"""
密码哈希工具

为测试提供密码哈希功能，与 FastAPI Users 内部使用的密码哈希方式保持一致。
"""
from passlib.context import CryptContext

# 创建密码上下文（与 FastAPI Users 默认配置一致）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_password_hash(password: str) -> str:
    """
    生成密码哈希
    
    Args:
        password: 明文密码
        
    Returns:
        BCrypt 哈希后的密码
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希后的密码
        
    Returns:
        密码是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)

