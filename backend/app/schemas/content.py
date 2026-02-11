"""
内容相关 Schema 定义

用于教程、资源推荐、测验等学习内容的数据传输对象。
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TutorialItemResponse(BaseModel):
    """
    教程项响应
    
    单个教程版本的基本信息。
    """
    tutorial_id: str = Field(..., description="教程ID")
    title: str = Field(..., description="教程标题")
    summary: Optional[str] = Field(None, description="教程摘要")
    content_url: Optional[str] = Field(None, description="内容URL（S3）")
    content_version: int = Field(..., description="内容版本号")
    is_latest: bool = Field(..., description="是否为最新版本")
    content_status: str = Field(..., description="内容生成状态")
    created_at: Optional[str] = Field(None, description="创建时间（ISO格式）")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tutorial_id": "tutorial-123",
                    "title": "Python基础入门",
                    "summary": "本教程介绍Python的基本语法",
                    "content_url": "s3://bucket/tutorials/123.md",
                    "content_version": 1,
                    "is_latest": True,
                    "content_status": "completed",
                    "created_at": "2026-01-07T10:00:00Z"
                }
            ]
        }
    }


class TutorialVersionListResponse(BaseModel):
    """
    教程版本列表响应
    
    包含概念的所有教程版本历史。
    """
    roadmap_id: str = Field(..., description="路线图ID")
    concept_id: str = Field(..., description="概念ID")
    total_versions: int = Field(..., description="总版本数")
    tutorials: List[TutorialItemResponse] = Field(..., description="教程列表")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "roadmap_id": "roadmap-456",
                    "concept_id": "concept-789",
                    "total_versions": 3,
                    "tutorials": []
                }
            ]
        }
    }


class TutorialDetailResponse(BaseModel):
    """
    教程详情响应
    
    单个教程版本的完整信息。
    """
    roadmap_id: str = Field(..., description="路线图ID")
    concept_id: str = Field(..., description="概念ID")
    tutorial_id: str = Field(..., description="教程ID")
    title: str = Field(..., description="教程标题")
    summary: Optional[str] = Field(None, description="教程摘要")
    content_url: Optional[str] = Field(None, description="内容URL（S3）")
    content_version: int = Field(..., description="内容版本号")
    is_latest: bool = Field(..., description="是否为最新版本")
    content_status: str = Field(..., description="内容生成状态")
    estimated_completion_time: Optional[int] = Field(None, description="预计完成时间（分钟）")
    created_at: Optional[str] = Field(None, description="创建时间（ISO格式）")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "roadmap_id": "roadmap-456",
                    "concept_id": "concept-789",
                    "tutorial_id": "tutorial-123",
                    "title": "Python基础入门",
                    "summary": "本教程介绍Python的基本语法",
                    "content_url": "s3://bucket/tutorials/123.md",
                    "content_version": 2,
                    "is_latest": True,
                    "content_status": "completed",
                    "estimated_completion_time": 30,
                    "created_at": "2026-01-07T10:00:00Z"
                }
            ]
        }
    }


class ResourcesResponse(BaseModel):
    """
    资源推荐响应
    
    概念的学习资源推荐信息。
    """
    roadmap_id: str = Field(..., description="路线图ID")
    concept_id: str = Field(..., description="概念ID")
    resources_id: str = Field(..., description="资源记录ID")
    resources: List[Dict[str, Any]] = Field(..., description="资源列表")
    resources_count: int = Field(..., description="资源数量")
    search_queries_used: Optional[List[str]] = Field(None, description="使用的搜索查询")
    created_at: Optional[str] = Field(None, description="创建时间（ISO格式）")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "roadmap_id": "roadmap-456",
                    "concept_id": "concept-789",
                    "resources_id": "resources-123",
                    "resources": [
                        {
                            "title": "Python官方文档",
                            "url": "https://docs.python.org",
                            "type": "documentation",
                            "score": 0.95
                        }
                    ],
                    "resources_count": 5,
                    "search_queries_used": ["Python tutorial", "Python best practices"],
                    "created_at": "2026-01-07T10:00:00Z"
                }
            ]
        }
    }


class QuizResponse(BaseModel):
    """
    测验响应
    
    概念的测验题目信息。
    """
    roadmap_id: str = Field(..., description="路线图ID")
    concept_id: str = Field(..., description="概念ID")
    quiz_id: str = Field(..., description="测验ID")
    questions: List[Dict[str, Any]] = Field(..., description="题目列表")
    total_questions: int = Field(..., description="总题目数")
    easy_count: int = Field(..., description="简单题数量")
    medium_count: int = Field(..., description="中等题数量")
    hard_count: int = Field(..., description="困难题数量")
    created_at: Optional[str] = Field(None, description="创建时间（ISO格式）")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "roadmap_id": "roadmap-456",
                    "concept_id": "concept-789",
                    "quiz_id": "quiz-123",
                    "questions": [
                        {
                            "question": "What is Python?",
                            "options": ["A", "B", "C", "D"],
                            "correct_answer": "A",
                            "difficulty": "easy"
                        }
                    ],
                    "total_questions": 10,
                    "easy_count": 4,
                    "medium_count": 4,
                    "hard_count": 2,
                    "created_at": "2026-01-07T10:00:00Z"
                }
            ]
        }
    }


class ContentSaveStatus(BaseModel):
    """
    内容保存状态
    
    记录单个 Concept 的各类内容保存状态。
    """
    concept_id: str = Field(..., description="概念ID")
    tutorial: str = Field(..., description="教程保存状态: success/failed/skipped")
    resource: str = Field(..., description="资源保存状态: success/failed/skipped")
    quiz: str = Field(..., description="测验保存状态: success/failed/skipped")
    metadata_saved: bool = Field(..., description="元数据是否全部保存成功")


class SubgraphGenerationResponse(BaseModel):
    """
    子图生成响应
    
    用于独立子图 API 的响应数据。
    """
    concept_id: str = Field(..., description="概念ID")
    roadmap_id: str = Field(..., description="路线图ID")
    save_status: ContentSaveStatus = Field(..., description="保存状态")
    tutorial_generated: bool = Field(..., description="是否生成了教程")
    resource_generated: bool = Field(..., description="是否生成了资源")
    quiz_generated: bool = Field(..., description="是否生成了测验")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="错误列表")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "concept_id": "concept-123",
                    "roadmap_id": "roadmap-456",
                    "save_status": {
                        "concept_id": "concept-123",
                        "tutorial": "success",
                        "resource": "success",
                        "quiz": "success",
                        "metadata_saved": True
                    },
                    "tutorial_generated": True,
                    "resource_generated": True,
                    "quiz_generated": True,
                    "errors": []
                }
            ]
        }
    }


# ============================================================
# Concept 状态相关
# ============================================================

class ConceptStatusResponse(BaseModel):
    """
    单个 Concept 状态响应
    
    用于查询 Concept 内容生成状态。
    """
    concept_id: str = Field(..., description="概念 ID")
    overall_status: str = Field(..., description="整体状态")
    tutorial_status: str = Field(..., description="教程状态")
    resources_status: str = Field(..., description="资源状态")
    quiz_status: str = Field(..., description="测验状态")
    tutorial_id: Optional[str] = Field(None, description="教程 ID")
    resources_id: Optional[str] = Field(None, description="资源 ID")
    quiz_id: Optional[str] = Field(None, description="测验 ID")
    all_content_completed_at: Optional[str] = Field(None, description="全部内容完成时间 (ISO 格式)")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "concept_id": "concept-123",
                    "overall_status": "completed",
                    "tutorial_status": "completed",
                    "resources_status": "completed",
                    "quiz_status": "completed",
                    "tutorial_id": "tutorial-123",
                    "resources_id": "resources-123",
                    "quiz_id": "quiz-123",
                    "all_content_completed_at": "2026-01-16T10:00:00Z"
                }
            ]
        }
    }


class RoadmapConceptsStatusResponse(BaseModel):
    """
    Roadmap 所有 Concept 状态响应
    
    用于批量查询某 roadmap 的所有 Concept 状态。
    """
    roadmap_id: str = Field(..., description="路线图 ID")
    total_concepts: int = Field(..., description="总概念数")
    completed_count: int = Field(..., description="已完成数量")
    concepts: List[ConceptStatusResponse] = Field(..., description="概念状态列表")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "roadmap_id": "roadmap-456",
                    "total_concepts": 10,
                    "completed_count": 7,
                    "concepts": []
                }
            ]
        }
    }


# ============================================================
# 内容修改相关
# ============================================================

class ModifyContentRequest(BaseModel):
    """
    修改内容请求
    
    用于教程、资源、测验的增量修改。
    """
    user_id: str = Field(..., description="用户 ID")
    preferences: "LearningPreferences" = Field(..., description="用户学习偏好")
    requirements: List[str] = Field(
        ...,
        description="修改要求列表",
        min_length=1,
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "user_id": "user-123",
                    "preferences": {
                        "learning_goal": "Learn Python",
                        "current_level": "intermediate",
                    },
                    "requirements": ["增加更多代码示例", "简化技术术语"]
                }
            ]
        }
    }


# ============================================================
# 子图生成相关
# ============================================================

class GenerateSingleConceptRequest(BaseModel):
    """
    生成单个 Concept 内容请求
    
    用于独立调用单 Concept 子图生成内容。
    """
    concept_id: str = Field(..., description="概念 ID")
    roadmap_id: str = Field(..., description="路线图 ID")
    force_regenerate: bool = Field(False, description="是否强制重新生成")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "concept_id": "concept-123",
                    "roadmap_id": "roadmap-456",
                    "force_regenerate": False
                }
            ]
        }
    }


class ContentGenerationTaskResponse(BaseModel):
    """
    内容生成任务响应
    
    返回 Celery 任务信息。
    """
    celery_task_id: str = Field(..., description="Celery 任务 ID")
    roadmap_id: str = Field(..., description="路线图 ID")
    concept_id: str = Field(..., description="概念 ID")
    status: str = Field("pending", description="任务状态")
    message: str = Field(..., description="提示信息")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "celery_task_id": "task-123-456",
                    "roadmap_id": "roadmap-456",
                    "concept_id": "concept-123",
                    "status": "pending",
                    "message": "任务已提交"
                }
            ]
        }
    }


# 引入 LearningPreferences（前向引用）
from app.models.domain import LearningPreferences
ModifyContentRequest.model_rebuild()

