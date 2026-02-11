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
    
    核心步骤：
    - 主路节点：INTENT_ANALYSIS → CURRICULUM_DESIGN → STRUCTURE_VALIDATION → HUMAN_REVIEW → CONTENT_GENERATION
    - 共享编辑节点：EDIT_PLAN_ANALYSIS、ROADMAP_EDIT（由edit_source区分来源）
    """
    # 初始化阶段
    INIT = "init"                                          # 初始化
    QUEUED = "queued"                                      # 已入队
    STARTING = "starting"                                  # 启动中
    
    # 主路节点
    INTENT_ANALYSIS = "intent_analysis"                    # 需求分析
    CURRICULUM_DESIGN = "curriculum_design"                # 课程设计
    STRUCTURE_VALIDATION = "structure_validation"          # 结构验证
    HUMAN_REVIEW = "human_review"                          # 人工审核
    
    # 共享编辑节点（由edit_source区分来源：validation_failed或human_review）
    EDIT_PLAN_ANALYSIS = "edit_plan_analysis"              # 编辑计划分析（共享）
    ROADMAP_EDIT = "roadmap_edit"                          # 路线图修正（共享）
    
    # 内容生成阶段
    CONTENT_GENERATION_QUEUED = "content_generation_queued"  # 内容生成已入队
    CONTENT_GENERATION = "content_generation"              # 内容生成（包含教程、资源、测验）
    
    # 完成阶段
    COMPLETED = "completed"                                # 已完成
    FAILED = "failed"                                      # 失败

