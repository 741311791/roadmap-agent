"""
获取用户画像工具

用于获取用户的个人画像信息，包括职业背景、技术栈、学习偏好等。
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import structlog

from app.tools.base import BaseTool
from app.db.repository_factory import get_repository_factory

logger = structlog.get_logger()


class GetUserProfileInput(BaseModel):
    """获取用户画像工具输入"""
    user_id: str = Field(..., description="用户 ID")


class GetUserProfileOutput(BaseModel):
    """获取用户画像工具输出"""
    success: bool = Field(..., description="是否成功")
    user_id: Optional[str] = Field(None, description="用户 ID")
    industry: Optional[str] = Field(None, description="所属行业")
    current_role: Optional[str] = Field(None, description="当前职位")
    tech_stack: List[Dict[str, Any]] = Field(default=[], description="技术栈")
    primary_language: str = Field(default="zh", description="主要语言")
    secondary_language: Optional[str] = Field(None, description="次要语言")
    weekly_commitment_hours: int = Field(default=10, description="每周学习时间")
    learning_style: List[str] = Field(default=[], description="学习风格偏好")
    ai_personalization: bool = Field(default=True, description="是否启用AI个性化")
    message: str = Field(..., description="结果消息")


class GetUserProfileTool(BaseTool[GetUserProfileInput, GetUserProfileOutput]):
    """
    获取用户画像工具
    
    功能：
    - 从数据库获取用户的个人画像
    - 返回职业背景、技术栈、学习偏好等信息
    - 用于个性化讲解和推荐
    """
    
    def __init__(self):
        super().__init__(tool_id="get_user_profile_v1")
        self.repo_factory = get_repository_factory()
    
    async def execute(self, input_data: GetUserProfileInput) -> GetUserProfileOutput:
        """
        获取用户画像
        
        Args:
            input_data: 查询参数
            
        Returns:
            用户画像信息
        """
        try:
            async with self.repo_factory.create_session() as session:
                user_profile_repo = self.repo_factory.create_user_profile_repo(session)
                
                profile = await user_profile_repo.get_by_user_id(input_data.user_id)
                
                if not profile:
                    logger.info(
                        "user_profile_not_found",
                        user_id=input_data.user_id,
                    )
                    
                    # 返回默认值
                    return GetUserProfileOutput(
                        success=True,
                        user_id=input_data.user_id,
                        message="用户尚未设置个人画像，使用默认值",
                    )
                
                logger.info(
                    "user_profile_found",
                    user_id=input_data.user_id,
                    industry=profile.industry,
                    current_role=profile.current_role,
                )
                
                return GetUserProfileOutput(
                    success=True,
                    user_id=profile.user_id,
                    industry=profile.industry,
                    current_role=profile.current_role,
                    tech_stack=profile.tech_stack or [],
                    primary_language=profile.primary_language,
                    secondary_language=profile.secondary_language,
                    weekly_commitment_hours=profile.weekly_commitment_hours,
                    learning_style=profile.learning_style or [],
                    ai_personalization=profile.ai_personalization,
                    message="成功获取用户画像",
                )
        
        except Exception as e:
            logger.error(
                "get_user_profile_failed",
                error=str(e),
                user_id=input_data.user_id,
            )
            
            return GetUserProfileOutput(
                success=False,
                message=f"获取用户画像失败: {str(e)}",
            )
