"""
FastAPI Users 认证策略

定义 JWT 认证策略，集成黑名单机制。

✅ v2.0 增强：
- 生成 Token 时自动添加 jti（JWT ID）
- 验证 Token 时检查黑名单
- 支持 Token 撤销（登出）
"""
from fastapi_users.authentication import JWTStrategy
from typing import Optional
import uuid
import structlog

from app.config.settings import settings
from app.core.auth.jwt_blacklist import is_blacklisted

logger = structlog.get_logger()


class BlacklistJWTStrategy(JWTStrategy):
    """
    支持黑名单的 JWT 认证策略
    
    扩展 FastAPI Users 的 JWTStrategy，添加：
    1. 自动生成 jti（JWT ID）
    2. 验证时检查黑名单
    """
    
    async def write_token(self, user) -> str:
        """
        生成 JWT Token
        
        覆盖父类方法，自动添加 jti 字段
        """
        # 生成唯一的 jti（JWT ID）
        jti = str(uuid.uuid4())
        
        # 手动编码 JWT Token（添加 jti 字段）
        from jose import jwt
        import time
        
        payload = {
            "sub": str(user.id),
            "jti": jti,
            "exp": int(time.time()) + self.lifetime_seconds,
        }
        
        # ✅ 安全获取 secret（兼容 str 和 SecretStr）
        secret_value = (
            self.secret.get_secret_value() 
            if hasattr(self.secret, 'get_secret_value') 
            else self.secret
        )
        
        token = jwt.encode(
            payload,
            secret_value,
            algorithm=self.algorithm,
        )
        
        logger.debug("jwt_token_generated", jti=jti, user_id=user.id)
        
        return token
    
    async def read_token(
        self, token: Optional[str], user_manager
    ) -> Optional[str]:
        """
        验证 JWT Token
        
        策略：先检查黑名单，然后调用父类验证
        """
        if token is None:
            return None
        
        # ✅ 步骤1：提取 jti 并检查黑名单（在完整验证之前，快速失败）
        try:
            from jose import jwt, JWTError
            
            # 仅解码 Token（不验证签名），获取 jti
            unverified_payload = jwt.get_unverified_claims(token)
            jti = unverified_payload.get("jti")
            
            # 检查黑名单
            if jti and await is_blacklisted(jti):
                logger.warning(
                    "jwt_token_blacklisted",
                    jti=jti,
                    message="Token 已被撤销",
                )
                return None
            
        except JWTError as e:
            logger.debug("jwt_token_decode_failed", error=str(e))
            return None
        
        # ✅ 步骤2：调用父类方法完成完整验证（签名、过期时间等）
        # 父类会返回 user_id，FastAPI Users 会用它查询 User 对象
        return await super().read_token(token, user_manager)


def get_jwt_strategy() -> BlacklistJWTStrategy:
    """
    获取 JWT 认证策略（带黑名单支持）
    
    Returns:
        BlacklistJWTStrategy 实例
    """
    return BlacklistJWTStrategy(
        secret=settings.JWT_SECRET_KEY,
        lifetime_seconds=settings.JWT_LIFETIME_SECONDS,
        algorithm=settings.JWT_ALGORITHM,
        token_audience=None,  # ✅ 禁用 audience 验证（简化JWT payload）
    )

