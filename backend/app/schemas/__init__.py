"""
Schemas统一导出
"""

# 通用Schemas
from app.schemas.common import (
    ErrorResponse,
    ErrorDetail,
    SuccessResponse,
    PaginationParams,
    PaginatedResponse,
    TaskStatus,
)

# 路线图Schemas
from app.schemas.roadmap import (
    RoadmapGenerateRequest,
    RoadmapGenerateResponse,
    RoadmapUpdateRequest,
    RoadmapCreate,
    RoadmapUpdate,
    RoadmapSummary,
    RoadmapDetail,
    RoadmapListResponse,
    ConceptRetryRequest,
    ConceptRetryResponse,
)

# 概念Schemas
from app.schemas.concept import (
    ConceptCreate,
    ConceptUpdate,
    ConceptDetail,
    ConceptSummary,
)

# 教程Schemas
from app.schemas.tutorial import (
    TutorialRetryRequest,
    TutorialRetryResponse,
    TutorialCreate,
    TutorialUpdate,
    TutorialDetail,
)

# 资源Schemas
from app.schemas.resource import (
    ResourceRetryRequest,
    ResourceRetryResponse,
    ResourceCreate,
    ResourceUpdate,
    ResourceDetail,
)

# 测验Schemas
from app.schemas.quiz import (
    QuizRetryRequest,
    QuizRetryResponse,
    QuizCreate,
    QuizUpdate,
    QuizSubmitRequest,
    QuizDetail,
    QuizSubmitResponse,
)

# 伴学Schemas
from app.schemas.mentor import (
    ChatStreamRequest,
    ChatSessionResponse,
    ChatMessageResponse,
    LearningNoteResponse,
    LearningNoteCreate,
    LearningNoteUpdate,
    PaginatedChatSessionsResponse,
    PaginatedChatMessagesResponse,
    PaginatedLearningNotesResponse,
)

# 用户Schemas
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserLogin,
    UserResponse,
    UserLoginResponse,
    UserProfile,
    UserProfileResponse,
    RoadmapHistoryResponse,
    TaskListResponse,
    DeletedRoadmapsResponse,
)

# 任务Schemas
from app.schemas.task import (
    TaskStatusDetailResponse,
)

# 封面图Schemas
from app.schemas.cover_image import (
    CoverImageStatusResponse,
)

# 任务恢复Schemas
from app.schemas.task_recovery import (
    TaskRecoveryReport,
)

# 内容重试Schemas
from app.schemas.content_retry import (
    ContentRetryResult,
)

# Tavily Schemas
from app.schemas.tavily import (
    TavilyAllocationStats,
)

# 进度Schemas
from app.schemas.progress import (
    ProgressCreate,
    ProgressUpdate,
    ProgressDetail,
    RoadmapProgressSummary,
)

# 技术评估Schemas
from app.schemas.tech_assessment import (
    TechAssessmentCreate,
    TechAssessmentSubmit,
    TechAssessmentResponse,
    TechAssessmentResult,
)

__all__ = [
    # Common
    "ErrorResponse",
    "ErrorDetail",
    "SuccessResponse",
    "PaginationParams",
    "PaginatedResponse",
    "TaskStatus",
    # Roadmap
    "RoadmapGenerateRequest",
    "RoadmapGenerateResponse",
    "RoadmapUpdateRequest",
    "RoadmapCreate",
    "RoadmapUpdate",
    "RoadmapSummary",
    "RoadmapDetail",
    "RoadmapListResponse",
    "ConceptRetryRequest",
    "ConceptRetryResponse",
    # Concept
    "ConceptCreate",
    "ConceptUpdate",
    "ConceptDetail",
    "ConceptSummary",
    # Tutorial
    "TutorialRetryRequest",
    "TutorialRetryResponse",
    "TutorialCreate",
    "TutorialUpdate",
    "TutorialDetail",
    # Resource
    "ResourceRetryRequest",
    "ResourceRetryResponse",
    "ResourceCreate",
    "ResourceUpdate",
    "ResourceDetail",
    # Quiz
    "QuizRetryRequest",
    "QuizRetryResponse",
    "QuizCreate",
    "QuizUpdate",
    "QuizSubmitRequest",
    "QuizDetail",
    "QuizSubmitResponse",
    # Mentor
    "MentorChatRequest",
    "MentorChatResponse",
    "MentorFeedbackRequest",
    "MentorFeedbackResponse",
    # User
    "UserCreate",
    "UserUpdate",
    "UserLogin",
    "UserResponse",
    "UserLoginResponse",
    "UserProfile",
    "UserProfileResponse",
    "RoadmapHistoryResponse",
    "TaskListResponse",
    "DeletedRoadmapsResponse",
    # Task
    "TaskStatusDetailResponse",
    # Cover Image
    "CoverImageStatusResponse",
    # Task Recovery
    "TaskRecoveryReport",
    # Content Retry
    "ContentRetryResult",
    # Tavily
    "TavilyAllocationStats",
    # Progress
    "ProgressCreate",
    "ProgressUpdate",
    "ProgressDetail",
    "RoadmapProgressSummary",
    # Tech Assessment
    "TechAssessmentCreate",
    "TechAssessmentSubmit",
    "TechAssessmentResponse",
    "TechAssessmentResult",
]

