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
    
    状态说明：
    - available=True: 数据已生成，所有字段有效
    - available=False: 数据尚未生成，仅 status/current_step/message 有效
    """
    # ✅ 新增 available 字段指示数据是否可用
    available: bool = Field(True, description="数据是否可用")
    
    # ✅ 以下字段在 available=False 时为 None
    intent_id: Optional[str] = Field(None, description="意图分析ID（主键）")
    roadmap_id: Optional[str] = Field(None, description="路线图ID")
    parsed_goal: Optional[str] = Field(None, description="解析后的学习目标")
    key_technologies: Optional[list[str]] = Field(None, description="关键技术列表")
    difficulty_profile: Optional[str] = Field(None, description="难度画像")
    time_constraint: Optional[str] = Field(None, description="时间限制")
    recommended_focus: Optional[list[str]] = Field(None, description="推荐重点")
    user_profile_summary: Optional[str] = Field(None, description="用户画像摘要")
    skill_gap_analysis: Optional[list[str]] = Field(None, description="技能差距分析")
    personalized_suggestions: Optional[list[str]] = Field(None, description="个性化建议")
    estimated_learning_path_type: Optional[str] = Field(None, description="预估学习路径类型")
    content_format_weights: Optional[dict] = Field(None, description="内容格式权重")
    language_preferences: Optional[dict] = Field(None, description="语言偏好")
    created_at: Optional[str] = Field(None, description="创建时间（ISO格式）")
    
    # ✅ 新增任务状态字段（available=False 时有值）
    status: Optional[str] = Field(None, description="任务状态")
    current_step: Optional[str] = Field(None, description="当前步骤")
    message: Optional[str] = Field(None, description="状态消息")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "intent_id": "intent-123",
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

