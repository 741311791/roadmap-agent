"""
用户画像 Repository

负责 UserProfile 表的数据访问操作。

职责范围：
- 用户画像的 CRUD 操作
- 用户偏好设置查询和更新

不包含：
- 用户画像分析逻辑（在 Service 层）
- 个性化推荐计算（在 Agent 层）
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import UserProfile, beijing_now
from .base import BaseRepository
import structlog

logger = structlog.get_logger(__name__)


class UserProfileRepository(BaseRepository[UserProfile]):
    """
    用户画像数据访问层
    
    管理用户个人偏好设置。
    """
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserProfile)
    
    # ============================================================
    # 查询方法
    # ============================================================
    
    async def get_by_user_id(self, user_id: str) -> Optional[UserProfile]:
        """
        获取用户画像
        
        Args:
            user_id: 用户 ID
            
        Returns:
            用户画像，如果不存在则返回 None
        """
        profile = await self.get_by_id(user_id)
        
        if profile:
            logger.debug(
                "user_profile_found",
                user_id=user_id,
                primary_language=profile.primary_language,
                ai_personalization=profile.ai_personalization,
            )
        
        return profile
    
    # ============================================================
    # 创建和更新方法
    # ============================================================
    
    async def save_user_profile(
        self,
        user_id: str,
        profile_data: dict,
    ) -> UserProfile:
        """
        保存或更新用户画像
        
        Args:
            user_id: 用户 ID
            profile_data: 用户画像数据
            
        Returns:
            保存的用户画像记录
        """
        existing = await self.get_by_user_id(user_id)
        
        if existing:
            # 更新现有记录
            update_data = {
                k: v for k, v in profile_data.items()
                if hasattr(UserProfile, k)
            }
            update_data["updated_at"] = beijing_now()
            
            await self.update_by_id(user_id, **update_data)
            
            # 重新获取更新后的记录
            updated = await self.get_by_user_id(user_id)
            
            logger.info("user_profile_updated", user_id=user_id)
            
            return updated
        else:
            # 创建新记录
            profile = UserProfile(
                user_id=user_id,
                industry=profile_data.get("industry"),
                current_role=profile_data.get("current_role"),
                tech_stack=profile_data.get("tech_stack", []),
                primary_language=profile_data.get("primary_language", "zh"),
                secondary_language=profile_data.get("secondary_language"),
                weekly_commitment_hours=profile_data.get("weekly_commitment_hours", 10),
                learning_style=profile_data.get("learning_style", []),
                ai_personalization=profile_data.get("ai_personalization", True),
                created_at=beijing_now(),
                updated_at=beijing_now(),
            )
            
            await self.create(profile, flush=True)
            
            logger.info("user_profile_created", user_id=user_id)
            
            return profile
    
    async def update_learning_style(
        self,
        user_id: str,
        learning_style: list,
    ) -> bool:
        """
        更新用户的学习风格偏好
        
        Args:
            user_id: 用户 ID
            learning_style: 学习风格列表 ['visual', 'text', 'audio', 'hands_on']
            
        Returns:
            True 如果更新成功，False 如果用户不存在
        """
        return await self.update_by_id(
            user_id,
            learning_style=learning_style,
            updated_at=beijing_now(),
        )
    
    async def update_language_preferences(
        self,
        user_id: str,
        primary_language: str,
        secondary_language: Optional[str] = None,
    ) -> bool:
        """
        更新用户的语言偏好
        
        Args:
            user_id: 用户 ID
            primary_language: 主要语言
            secondary_language: 次要语言（可选）
            
        Returns:
            True 如果更新成功，False 如果用户不存在
        """
        update_data = {
            "primary_language": primary_language,
            "updated_at": beijing_now(),
        }
        
        if secondary_language:
            update_data["secondary_language"] = secondary_language
        
        return await self.update_by_id(user_id, **update_data)
    
    async def toggle_ai_personalization(
        self,
        user_id: str,
        enabled: bool,
    ) -> bool:
        """
        切换 AI 个性化开关
        
        Args:
            user_id: 用户 ID
            enabled: 是否启用
            
        Returns:
            True 如果更新成功，False 如果用户不存在
        """
        return await self.update_by_id(
            user_id,
            ai_personalization=enabled,
            updated_at=beijing_now(),
        )
    
    # ============================================================
    # 删除方法
    # ============================================================
    
    async def delete_user_profile(self, user_id: str) -> bool:
        """
        删除用户画像
        
        Args:
            user_id: 用户 ID
            
        Returns:
            True 如果删除成功，False 如果用户不存在
        """
        deleted = await self.delete_by_id(user_id)
        
        if deleted:
            logger.info("user_profile_deleted", user_id=user_id)
        
        return deleted
