"""
Handler层 - 副作用处理器

负责处理工作流节点的副作用（数据库保存、日志记录、通知发布）
遵循LangGraph 1.0最佳实践：Node纯函数化，副作用在Stream Loop中统一处理
"""
from .base import NodeOutputHandler
from .registry import HandlerRegistry
from .intent_handler import IntentAnalysisHandler
from .curriculum_handler import CurriculumDesignHandler
from .validation_handler import ValidationHandler
from .editor_handler import EditorHandler
from .review_handler import ReviewHandler
from .content_handler import ContentHandler
from .edit_plan_handler import EditPlanHandler
# ✅ 移除：ValidationEditPlanHandler（使用共享的EditPlanHandler）

__all__ = [
    "NodeOutputHandler",
    "HandlerRegistry",
    "IntentAnalysisHandler",
    "CurriculumDesignHandler",
    "ValidationHandler",
    "EditorHandler",
    "ReviewHandler",
    "ContentHandler",
    "EditPlanHandler",
    # ✅ 移除：ValidationEditPlanHandler
]

