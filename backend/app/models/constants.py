"""
常量定义模块

定义应用中使用的枚举和常量值。
"""
from enum import Enum


class TaskStatus(str, Enum):
    """
    任务状态枚举
    
    与前端 TaskStatus 完全对齐。
    """
    PENDING = "pending"                    # 待处理
    PROCESSING = "processing"              # 处理中
    HUMAN_REVIEW = "human_review_pending"  # 等待人工审核
    COMPLETED = "completed"                # 已完成
    PARTIAL_FAILURE = "partial_failure"    # 部分失败
    FAILED = "failed"                      # 失败
    CANCELLED = "cancelled"                # 已取消


class ContentStatus(str, Enum):
    """
    内容生成状态枚举
    """
    PENDING = "pending"                    # 待生成
    COMPLETED = "completed"                # 已完成
    FAILED = "failed"                      # 失败


class WorkflowStep(str, Enum):
    """
    工作流步骤枚举
    """
    INIT = "init"                                          # 初始化
    QUEUED = "queued"                                      # 已入队
    STARTING = "starting"                                  # 启动中
    INTENT_ANALYSIS = "intent_analysis"                    # 需求分析
    CURRICULUM_DESIGN = "curriculum_design"                # 课程设计
    STRUCTURE_VALIDATION = "structure_validation"          # 结构验证
    VALIDATION_EDIT_PLAN_ANALYSIS = "validation_edit_plan_analysis"  # 验证修改计划分析
    EDIT_PLAN_ANALYSIS = "edit_plan_analysis"              # 审核修改计划分析
    ROADMAP_EDIT = "roadmap_edit"                          # 路线图修正
    HUMAN_REVIEW = "human_review"                          # 人工审核
    CONTENT_GENERATION_QUEUED = "content_generation_queued"  # 内容生成已入队
    CONTENT_GENERATION = "content_generation"              # 内容生成
    TUTORIAL_GENERATION = "tutorial_generation"            # 教程生成
    RESOURCE_RECOMMENDATION = "resource_recommendation"    # 资源推荐
    QUIZ_GENERATION = "quiz_generation"                    # 测验生成
    FINALIZING = "finalizing"                              # 收尾中
    COMPLETED = "completed"                                # 已完成
    FAILED = "failed"                                      # 失败

