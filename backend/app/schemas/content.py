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
    generated_at: Optional[str] = Field(None, description="生成时间（ISO格式）")
    
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
                    "generated_at": "2026-01-07T10:00:00Z"
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
    generated_at: Optional[str] = Field(None, description="生成时间（ISO格式）")
    
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
                    "generated_at": "2026-01-07T10:00:00Z"
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
    generated_at: Optional[str] = Field(None, description="生成时间（ISO格式）")
    
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
                    "generated_at": "2026-01-07T10:00:00Z"
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
    generated_at: Optional[str] = Field(None, description="生成时间（ISO格式）")
    
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
                    "generated_at": "2026-01-07T10:00:00Z"
                }
            ]
        }
    }

