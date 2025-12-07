"""
Repository 层

职责：数据访问层，负责与数据库交互

模块说明：
- base.py: 基础 Repository，提供通用 CRUD 操作
- task_repo.py: 任务数据访问
- roadmap_meta_repo.py: 路线图元数据访问
- tutorial_repo.py: 教程数据访问
- resource_repo.py: 资源推荐数据访问
- quiz_repo.py: 测验数据访问
- intent_analysis_repo.py: 需求分析数据访问
- user_profile_repo.py: 用户画像数据访问
- execution_log_repo.py: 执行日志数据访问
- roadmap_repo.py: 旧版路线图 Repository（待弃用）

Factory:
- repository_factory.py: Repository 工厂，统一创建 Repository 实例
"""

from .base import BaseRepository
from .task_repo import TaskRepository
from .roadmap_meta_repo import RoadmapMetadataRepository
from .tutorial_repo import TutorialRepository
from .resource_repo import ResourceRepository
from .quiz_repo import QuizRepository
from .intent_analysis_repo import IntentAnalysisRepository
from .user_profile_repo import UserProfileRepository
from .execution_log_repo import ExecutionLogRepository

# 旧版 Repository（向后兼容，待迁移完成后删除）
from .roadmap_repo import RoadmapRepository

__all__ = [
    # Base
    "BaseRepository",
    # New Repositories
    "TaskRepository",
    "RoadmapMetadataRepository",
    "TutorialRepository",
    "ResourceRepository",
    "QuizRepository",
    "IntentAnalysisRepository",
    "UserProfileRepository",
    "ExecutionLogRepository",
    # Legacy (to be deprecated)
    "RoadmapRepository",
]
