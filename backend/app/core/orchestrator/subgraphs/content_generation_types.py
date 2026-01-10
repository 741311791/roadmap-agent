"""
内容生成子图的类型定义

使用 Pydantic 模型和枚举提供类型安全，避免字符串字面量。
"""
from enum import Enum
from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """内容类型枚举"""
    TUTORIAL = "tutorial"
    RESOURCE = "resource"
    QUIZ = "quiz"


class NodeName(str, Enum):
    """子图节点名称枚举"""
    FAN_OUT = "fan_out"
    GENERATE_TUTORIAL = "generate_tutorial"
    GENERATE_RESOURCE = "generate_resource"
    GENERATE_QUIZ = "generate_quiz"


class StateKey(str, Enum):
    """状态字段键名枚举"""
    # 输入字段
    ROADMAP_ID = "roadmap_id"
    CONCEPTS = "concepts"
    USER_PREFERENCES = "user_preferences"
    TASK_ID = "task_id"
    CONCEPT = "concept"
    CONTEXT = "context"
    
    # 输出字段
    TUTORIALS = "tutorials"
    RESOURCES = "resources"
    QUIZZES = "quizzes"
    ERRORS = "errors"


class ContextKey(str, Enum):
    """上下文字段键名枚举"""
    ROADMAP_ID = "roadmap_id"
    STAGE_NAME = "stage_name"
    MODULE_NAME = "module_name"


class ContentError(BaseModel):
    """
    内容生成错误模型
    
    使用 Pydantic 确保错误对象结构一致。
    """
    type: ContentType = Field(..., description="内容类型（tutorial/resource/quiz）")
    concept_id: str = Field(..., description="Concept ID")
    concept_name: str = Field(..., description="Concept 名称")
    error: str = Field(..., description="错误信息")
    
    class Config:
        use_enum_values = True  # 自动将枚举转换为值


class StateUpdate(BaseModel):
    """
    状态更新基类
    
    确保返回的状态更新结构一致。
    """
    class Config:
        arbitrary_types_allowed = True


class TutorialStateUpdate(StateUpdate):
    """教程生成状态更新"""
    tutorials: list = Field(default_factory=list, description="生成的教程列表")
    

class ResourceStateUpdate(StateUpdate):
    """资源推荐状态更新"""
    resources: list = Field(default_factory=list, description="推荐的资源列表")


class QuizStateUpdate(StateUpdate):
    """测验生成状态更新"""
    quizzes: list = Field(default_factory=list, description="生成的测验列表")


class ErrorStateUpdate(StateUpdate):
    """错误状态更新"""
    errors: list[dict] = Field(default_factory=list, description="错误列表")

