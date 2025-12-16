"""
FastAPI Users 认证策略

定义 JWT 认证策略。
"""
from fastapi_users.authentication import JWTStrategy

from app.config.settings import settings


def get_jwt_strategy() -> JWTStrategy:
    """
    获取 JWT 认证策略
    
    配置 JWT 令牌的生成和验证参数。
    
    Returns:
        JWTStrategy 实例
    """
    return JWTStrategy(
        secret=settings.JWT_SECRET_KEY,
        lifetime_seconds=settings.JWT_LIFETIME_SECONDS,
        algorithm=settings.JWT_ALGORITHM,
    )

