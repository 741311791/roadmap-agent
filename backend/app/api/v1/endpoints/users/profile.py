"""
用户画像 API 端点

提供用户画像的获取和保存功能。

重构变更：
- ✅ 从 users.py 拆分出来，专注于用户画像管理
- ✅ 移除了路线图列表、回收站、任务列表接口（已移到roadmaps/tasks）
- ✅ 使用统一响应格式（ResponseSchemaModel）
"""
from typing import Annotated
from fastapi import APIRouter, Depends
import structlog

from app.api.v1.deps import CurrentSession, CurrentSessionTransaction, CurrentUserService
from app.core.auth.deps import current_active_user
from app.models.database import User
from app.core.response_schema import ResponseSchemaModel, response_base

# ✅ 导入 Schema（符合企业级架构规范）
from app.schemas.user import (
    TechStackItem,
    UserProfileRequest,
    UserProfileResponse,
)

router = APIRouter(prefix="/users", tags=["users"])
logger = structlog.get_logger()


@router.get("/profile", response_model=ResponseSchemaModel[UserProfileResponse])
async def get_user_profile(
    db: CurrentSession,
    service: CurrentUserService,
    current_user: User = Depends(current_active_user),
) -> ResponseSchemaModel[UserProfileResponse]:
    """
    获取用户画像（从JWT自动提取user_id）
    
    Args:
        db: 数据库会话
        current_user: 当前用户（从JWT提取）
        service: 用户服务
        
    Returns:
        用户画像数据，如果不存在则返回默认值
        
    Example:
        ```json
        {
            "code": 200,
            "msg": "Success",
            "data": {
                "user_id": "user-123",
                "industry": "Technology",
                "current_role": "Software Engineer",
                "tech_stack": [
                    {
                        "technology": "Python",
                        "proficiency": "intermediate",
                        "capability_analysis": {}
                    }
                ],
                "primary_language": "zh",
                "weekly_commitment_hours": 10,
                "learning_style": ["text", "hands_on"],
                "ai_personalization": true
            }
        }
        ```
    """
    user_id = current_user.id  # 从JWT提取user_id
    logger.info("get_user_profile_requested", user_id=user_id)
    
    profile = await service.get_user_profile(db, user_id)
    
    if profile:
        return response_base.success(data=profile)
    else:
        # 返回默认画像
        return response_base.success(data=UserProfileResponse(
            user_id=user_id,
            tech_stack=[],
            learning_style=[],
        ))


@router.put("/profile", response_model=ResponseSchemaModel[UserProfileResponse])
async def save_user_profile(
    request: UserProfileRequest,
    db: CurrentSessionTransaction,
    service: CurrentUserService,
    current_user: User = Depends(current_active_user),
) -> ResponseSchemaModel[UserProfileResponse]:
    """
    保存或更新用户画像（从JWT自动提取user_id）
    
    Args:
        request: 用户画像数据
        db: 数据库会话（自动commit/rollback）
        current_user: 当前用户（从JWT提取）
        service: 用户服务
        
    Returns:
        保存后的用户画像
        
    Example Request:
        ```json
        {
            "industry": "Technology",
            "current_role": "Software Engineer",
            "tech_stack": [
                {
                    "technology": "Python",
                    "proficiency": "intermediate"
                }
            ],
            "primary_language": "zh",
            "weekly_commitment_hours": 15,
            "learning_style": ["text", "hands_on"],
            "ai_personalization": true
        }
        ```
    """
    user_id = current_user.id  # 从JWT提取user_id
    logger.info(
        "save_user_profile_requested",
        user_id=user_id,
        tech_stack_count=len(request.tech_stack),
    )
    
    # 转换为字典格式
    profile_data = {
        "industry": request.industry,
        "current_role": request.current_role,
        "tech_stack": [item.model_dump() for item in request.tech_stack],
        "primary_language": request.primary_language,
        "secondary_language": request.secondary_language,
        "weekly_commitment_hours": request.weekly_commitment_hours,
        "learning_style": request.learning_style,
        "ai_personalization": request.ai_personalization,
    }
    
    profile = await service.save_user_profile(db, user_id, profile_data)
    
    # ✅ 自动 commit
    
    return response_base.success(data=profile)

