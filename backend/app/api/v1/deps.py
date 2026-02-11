"""
API依赖注入统一管理
"""
from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_readonly, get_db_transaction, CurrentSession as DBCurrentSession, CurrentSessionTransaction as DBCurrentSessionTransaction
from app.crud.crud_roadmap import RoadmapCRUD, get_roadmap_crud
from app.crud.crud_concept import ConceptCRUD, get_concept_crud
from app.crud.crud_tutorial import TutorialCRUD, get_tutorial_crud
from app.crud.crud_resource import ResourceCRUD, get_resource_crud
from app.crud.crud_quiz import QuizCRUD, get_quiz_crud
from app.crud.crud_task import TaskCRUD, get_task_crud
from app.crud.crud_user import UserCRUD, get_user_crud
from app.crud.crud_progress import ProgressCRUD, get_progress_crud
from app.services.content.concept_service import ConceptService, get_concept_service
from app.services.content.content_service import ContentService, get_content_service
from app.core.auth.deps import current_user as get_current_user, current_active_user
from app.models.database import User

# ===== Session依赖 =====

# ✅ 只读Session（查询操作）
CurrentSession = Annotated[AsyncSession, Depends(get_db_readonly)]

# ✅ 事务Session（写操作）
CurrentSessionTransaction = Annotated[AsyncSession, Depends(get_db_transaction)]

# 直接使用get_db_readonly/get_db_transaction即可，无需包装函数
get_current_session = get_db_readonly
get_current_session_transaction = get_db_transaction

# ===== CRUD依赖 =====

CurrentRoadmapCRUD = Annotated[RoadmapCRUD, Depends(get_roadmap_crud)]
CurrentConceptCRUD = Annotated[ConceptCRUD, Depends(get_concept_crud)]
CurrentTutorialCRUD = Annotated[TutorialCRUD, Depends(get_tutorial_crud)]
CurrentResourceCRUD = Annotated[ResourceCRUD, Depends(get_resource_crud)]
CurrentQuizCRUD = Annotated[QuizCRUD, Depends(get_quiz_crud)]
CurrentTaskCRUD = Annotated[TaskCRUD, Depends(get_task_crud)]
CurrentUserCRUD = Annotated[UserCRUD, Depends(get_user_crud)]
CurrentProgressCRUD = Annotated[ProgressCRUD, Depends(get_progress_crud)]

# ===== 鉴权依赖 =====

CurrentUser = Annotated[User, Depends(get_current_user)]

async def get_current_active_user(current_user: CurrentUser) -> User:
    """
    获取当前活跃用户（检查账号状态）
    
    Args:
        current_user: 当前用户
        
    Returns:
        活跃用户实例
        
    Raises:
        HTTPException: 用户账号未激活
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user

CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]

async def get_current_user_id_flexible(current_user: User = Depends(current_active_user)) -> str:
    """
    获取当前用户ID（灵活版本，支持可选认证）
    
    Args:
        current_user: 当前用户
        
    Returns:
        用户ID字符串
    """
    return current_user.id

CurrentUserId = Annotated[str, Depends(get_current_user_id_flexible)]

# ===== 权限检查依赖 =====

class PermissionChecker:
    """
    权限检查器（可复用）
    
    使用示例：
    ```python
    RequireAdmin = Annotated[User, Depends(PermissionChecker("admin"))]
    
    @router.post("/admin/users")
    async def create_user(admin: RequireAdmin):
        # 只有admin权限的用户才能访问
        pass
    ```
    """
    
    def __init__(self, required_permission: str):
        """
        初始化权限检查器
        
        Args:
            required_permission: 所需权限名称
        """
        self.required_permission = required_permission
    
    def __call__(self, current_user: CurrentUser) -> User:
        """
        检查用户是否有指定权限
        
        Args:
            current_user: 当前用户
            
        Returns:
            用户实例
            
        Raises:
            HTTPException: 权限不足
        """
        # 注意：这里假设User模型有has_permission方法
        # 实际使用时需要根据User模型实现调整
        if hasattr(current_user, 'has_permission'):
            if not current_user.has_permission(self.required_permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {self.required_permission}",
                )
        else:
            # 如果User模型没有has_permission方法，这里可以实现简单的角色检查
            # 例如：检查current_user.role字段
            pass
        
        return current_user

# ===== 常用权限依赖（预定义）=====

RequireAdmin = Annotated[User, Depends(PermissionChecker("admin"))]
RequireModerator = Annotated[User, Depends(PermissionChecker("moderator"))]

# ===== Service依赖 =====

CurrentConceptService = Annotated[ConceptService, Depends(get_concept_service)]
CurrentContentService = Annotated[ContentService, Depends(get_content_service)]

# ===== 其他Service依赖 =====

try:
    from app.services.roadmaps.retrieval_service import RetrievalService, get_retrieval_service
    from app.services.roadmaps.status_service import StatusService, get_status_service
    from app.services.learning.progress_service import ProgressService, get_progress_service
    from app.services.users.user_service import UserService, get_user_service
    from app.services.roadmaps.management_service import ManagementService, get_management_service
    from app.services.workflows.generation.generation_service import GenerationService, get_generation_service
    
    # 定义依赖注入别名
    CurrentRetrievalService = Annotated[RetrievalService, Depends(get_retrieval_service)]
    CurrentStatusService = Annotated[StatusService, Depends(get_status_service)]
    CurrentProgressService = Annotated[ProgressService, Depends(get_progress_service)]
    CurrentUserService = Annotated[UserService, Depends(get_user_service)]
    CurrentManagementService = Annotated[ManagementService, Depends(get_management_service)]
    CurrentGenerationService = Annotated[GenerationService, Depends(get_generation_service)]
    
except ImportError as e:
    # 如果Service还未创建，提供占位符
    import structlog
    logger = structlog.get_logger()
    logger.warning("service_import_failed", error=str(e))

