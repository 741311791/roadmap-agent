"""
需求分析 Schema 定义

用于需求分析元数据的数据传输对象。
"""
from typing import Optional
from pydantic import BaseModel, Field


class IntentAnalysisResponse(BaseModel):
    """
    需求分析响应
    
    包含路线图生成过程中的需求分析结果。
    """
    id: str = Field(..., description="分析记录ID")
    task_id: str = Field(..., description="任务ID")
    roadmap_id: Optional[str] = Field(None, description="路线图ID")
    parsed_goal: str = Field(..., description="解析后的学习目标")
    key_technologies: list[str] = Field(..., description="关键技术列表")
    difficulty_profile: str = Field(..., description="难度画像")
    time_constraint: str = Field(..., description="时间限制")
    recommended_focus: list[str] = Field(..., description="推荐重点")
    user_profile_summary: Optional[str] = Field(None, description="用户画像摘要")
    skill_gap_analysis: list[str] = Field(..., description="技能差距分析")
    personalized_suggestions: list[str] = Field(..., description="个性化建议")
    estimated_learning_path_type: Optional[str] = Field(None, description="预估学习路径类型")
    content_format_weights: Optional[dict] = Field(None, description="内容格式权重")
    language_preferences: Optional[dict] = Field(None, description="语言偏好")
    created_at: Optional[str] = Field(None, description="创建时间（ISO格式）")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": "intent-123",
                    "task_id": "task-456",
                    "roadmap_id": "roadmap-789",
                    "parsed_goal": "学习Python Web开发",
                    "key_technologies": ["Python", "FastAPI", "PostgreSQL"],
                    "difficulty_profile": "intermediate",
                    "time_constraint": "3个月",
                    "recommended_focus": ["后端开发", "API设计"],
                    "user_profile_summary": "有基础编程经验",
                    "skill_gap_analysis": ["需要学习异步编程", "数据库优化"],
                    "personalized_suggestions": ["建议从FastAPI基础开始"],
                    "estimated_learning_path_type": "structured",
                    "content_format_weights": {"text": 0.6, "video": 0.4},
                    "language_preferences": {"primary": "zh", "secondary": "en"},
                    "created_at": "2026-01-07T10:00:00Z"
                }
            ]
        }
    }

