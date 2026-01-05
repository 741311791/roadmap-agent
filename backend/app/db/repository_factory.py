"""
Repository Factory

统一创建和管理所有 Repository 实例。

设计模式：工厂模式
- 封装 Repository 的创建逻辑
- 确保所有 Repository 使用同一个数据库会话
- 简化依赖注入
"""
from typing import AsyncContextManager
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

# get_db 已废弃，改用 safe_session_with_retry（在 create_session 中延迟导入）
from app.db.repositories.base import BaseRepository
from app.db.repositories.task_repo import TaskRepository
from app.db.repositories.roadmap_meta_repo import RoadmapMetadataRepository
from app.db.repositories.tutorial_repo import TutorialRepository
from app.db.repositories.resource_repo import ResourceRepository
from app.db.repositories.quiz_repo import QuizRepository
from app.db.repositories.intent_analysis_repo import IntentAnalysisRepository
from app.db.repositories.user_profile_repo import UserProfileRepository
from app.db.repositories.execution_log_repo import ExecutionLogRepository
from app.db.repositories.chat_repo import ChatRepository
from app.db.repositories.note_repo import NoteRepository
from app.db.repositories.validation_repo import ValidationRepository
from app.db.repositories.edit_repo import EditRepository

import structlog

logger = structlog.get_logger(__name__)


class RepositoryFactory:
    """
    Repository 工厂类
    
    提供统一的 Repository 创建接口，确保所有 Repository 使用相同的数据库会话。
    
    使用示例：
    ```python
    # 方式1：使用上下文管理器（推荐）
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        task = await task_repo.get_by_task_id("task-123")
        await session.commit()
    
    # 方式2：手动管理会话
    session = await repo_factory.get_session()
    try:
        task_repo = repo_factory.create_task_repo(session)
        task = await task_repo.get_by_task_id("task-123")
        await session.commit()
    finally:
        await session.close()
    ```
    """
    
    def __init__(self):
        """初始化 Repository 工厂"""
        pass
    
    # ============================================================
    # 会话管理
    # ============================================================
    
    @asynccontextmanager
    async def create_session(self) -> AsyncContextManager[AsyncSession]:
        """
        创建数据库会话（上下文管理器）
        
        ⚠️ 重要设计变更（v2.0）：
        不再使用 `async for get_db()` 的方式，而是直接使用 `safe_session_with_retry()`。
        这样可以更可靠地控制事务边界，避免生成器交互导致的时序问题。
        
        调用者必须显式调用 `await session.commit()` 来提交事务。
        会话结束时会自动关闭连接。
        
        使用示例：
        ```python
        async with repo_factory.create_session() as session:
            # 使用 session 创建 Repository
            task_repo = repo_factory.create_task_repo(session)
            # 执行数据库操作
            task = await task_repo.get_by_task_id("task-123")
            # 必须显式提交事务
            await session.commit()
        # 会话自动关闭
        ```
        
        Yields:
            AsyncSession: 数据库会话
        """
        from app.db.session import safe_session_with_retry
        
        async with safe_session_with_retry() as session:
            yield session
    
    async def get_session(self) -> AsyncSession:
        """
        获取数据库会话（手动管理）
        
        ⚠️ 废弃警告：推荐使用 create_session() 上下文管理器，可自动处理会话关闭。
        
        注意：调用者负责关闭会话
        
        Returns:
            AsyncSession: 数据库会话
        """
        import warnings
        warnings.warn(
            "get_session() 已废弃，请使用 create_session() 上下文管理器",
            DeprecationWarning,
            stacklevel=2,
        )
        
        from app.db.session import AsyncSessionLocal
        return AsyncSessionLocal()
    
    # ============================================================
    # Repository 创建方法
    # ============================================================
    
    def create_task_repo(self, session: AsyncSession) -> TaskRepository:
        """
        创建任务 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            TaskRepository 实例
        """
        return TaskRepository(session)
    
    def create_roadmap_meta_repo(
        self,
        session: AsyncSession,
    ) -> RoadmapMetadataRepository:
        """
        创建路线图元数据 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            RoadmapMetadataRepository 实例
        """
        return RoadmapMetadataRepository(session)
    
    def create_tutorial_repo(self, session: AsyncSession) -> TutorialRepository:
        """
        创建教程 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            TutorialRepository 实例
        """
        return TutorialRepository(session)
    
    def create_resource_repo(self, session: AsyncSession) -> ResourceRepository:
        """
        创建资源推荐 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            ResourceRepository 实例
        """
        return ResourceRepository(session)
    
    def create_quiz_repo(self, session: AsyncSession) -> QuizRepository:
        """
        创建测验 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            QuizRepository 实例
        """
        return QuizRepository(session)
    
    def create_intent_analysis_repo(
        self,
        session: AsyncSession,
    ) -> IntentAnalysisRepository:
        """
        创建需求分析 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            IntentAnalysisRepository 实例
        """
        return IntentAnalysisRepository(session)
    
    def create_user_profile_repo(
        self,
        session: AsyncSession,
    ) -> UserProfileRepository:
        """
        创建用户画像 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            UserProfileRepository 实例
        """
        return UserProfileRepository(session)
    
    def create_execution_log_repo(
        self,
        session: AsyncSession,
    ) -> ExecutionLogRepository:
        """
        创建执行日志 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            ExecutionLogRepository 实例
        """
        return ExecutionLogRepository(session)
    
    def create_chat_repo(
        self,
        session: AsyncSession,
    ) -> ChatRepository:
        """
        创建聊天会话 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            ChatRepository 实例
        """
        return ChatRepository(session)
    
    def create_note_repo(
        self,
        session: AsyncSession,
    ) -> NoteRepository:
        """
        创建学习笔记 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            NoteRepository 实例
        """
        return NoteRepository(session)
    
    def create_validation_repo(
        self,
        session: AsyncSession,
    ) -> ValidationRepository:
        """
        创建结构验证记录 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            ValidationRepository 实例
        """
        return ValidationRepository(session)
    
    def create_edit_repo(
        self,
        session: AsyncSession,
    ) -> EditRepository:
        """
        创建路线图编辑记录 Repository
        
        Args:
            session: 数据库会话
            
        Returns:
            EditRepository 实例
        """
        return EditRepository(session)
    
    # ============================================================
    # 批量创建（便捷方法）
    # ============================================================
    
    def create_all_repos(self, session: AsyncSession) -> dict:
        """
        创建所有 Repository（便捷方法）
        
        Args:
            session: 数据库会话
            
        Returns:
            包含所有 Repository 的字典
        """
        return {
            "task": self.create_task_repo(session),
            "roadmap_meta": self.create_roadmap_meta_repo(session),
            "tutorial": self.create_tutorial_repo(session),
            "resource": self.create_resource_repo(session),
            "quiz": self.create_quiz_repo(session),
            "intent_analysis": self.create_intent_analysis_repo(session),
            "user_profile": self.create_user_profile_repo(session),
            "execution_log": self.create_execution_log_repo(session),
            "chat": self.create_chat_repo(session),
            "note": self.create_note_repo(session),
            "validation": self.create_validation_repo(session),
            "edit": self.create_edit_repo(session),
        }


# 全局单例实例
_repository_factory: RepositoryFactory | None = None


def get_repository_factory() -> RepositoryFactory:
    """
    获取 Repository 工厂单例
    
    Returns:
        RepositoryFactory 实例
    """
    global _repository_factory
    
    if _repository_factory is None:
        _repository_factory = RepositoryFactory()
        logger.info("repository_factory_created")
    
    return _repository_factory


# FastAPI 依赖注入
async def get_repo_factory() -> RepositoryFactory:
    """
    FastAPI 依赖注入：获取 Repository 工厂
    
    使用示例：
    ```python
    @router.post("/tasks")
    async def create_task(
        repo_factory: RepositoryFactory = Depends(get_repo_factory),
    ):
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            task = await task_repo.create_task(...)
            await session.commit()
    ```
    """
    return get_repository_factory()
