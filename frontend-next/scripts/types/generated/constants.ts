/**
 * 自动生成的常量类型定义
 * 
 * 从后端 backend/app/models/constants.py 生成
 * 
 * ⚠️ WARNING: 请勿手动修改此文件
 * Run `npm run generate:constants` 重新生成
 * 
 * Generated at: 2026-01-20T14:38:20.920Z
 */

/**
 * 任务状态枚举
 *     
 *     与前端 TaskStatus 完全对齐。
 */
export enum TaskStatus {
  /** 待处理 */
  PENDING = "pending",
  /** 处理中 */
  PROCESSING = "processing",
  /** 等待人工审核 */
  HUMAN_REVIEW = "human_review_pending",
  /** 已完成 */
  COMPLETED = "completed",
  /** 部分失败 */
  PARTIAL_FAILURE = "partial_failure",
  /** 失败 */
  FAILED = "failed",
  /** 已取消 */
  CANCELLED = "cancelled",
}

/**
 * TaskStatus 类型 (Union Type)
 */
export type TaskStatusType = "pending" | "processing" | "human_review_pending" | "completed" | "partial_failure" | "failed" | "cancelled";

/**
 * TaskStatus 类型守卫
 */
export function isTaskStatus(value: any): value is TaskStatusType {
  return [
    "pending",
    "processing",
    "human_review_pending",
    "completed",
    "partial_failure",
    "failed",
    "cancelled",
  ].includes(value);
}

/**
 * TaskStatus 标签映射
 */
export const TaskStatusLabels: Record<TaskStatusType, string> = {
  "pending": "待处理",
  "processing": "处理中",
  "human_review_pending": "等待人工审核",
  "completed": "已完成",
  "partial_failure": "部分失败",
  "failed": "失败",
  "cancelled": "已取消",
};

/**
 * 内容生成状态枚举
 */
export enum ContentStatus {
  /** 待生成 */
  PENDING = "pending",
  /** 已完成 */
  COMPLETED = "completed",
  /** 失败 */
  FAILED = "failed",
}

/**
 * ContentStatus 类型 (Union Type)
 */
export type ContentStatusType = "pending" | "completed" | "failed";

/**
 * ContentStatus 类型守卫
 */
export function isContentStatus(value: any): value is ContentStatusType {
  return [
    "pending",
    "completed",
    "failed",
  ].includes(value);
}

/**
 * ContentStatus 标签映射
 */
export const ContentStatusLabels: Record<ContentStatusType, string> = {
  "pending": "待生成",
  "completed": "已完成",
  "failed": "失败",
};

/**
 * 工作流步骤枚举
 */
export enum WorkflowStep {
  /** 初始化 */
  INIT = "init",
  /** 已入队 */
  QUEUED = "queued",
  /** 启动中 */
  STARTING = "starting",
  /** 需求分析 */
  INTENT_ANALYSIS = "intent_analysis",
  /** 课程设计 */
  CURRICULUM_DESIGN = "curriculum_design",
  /** 结构验证 */
  STRUCTURE_VALIDATION = "structure_validation",
  /** 验证修改计划分析 */
  // ✅ 移除：VALIDATION_EDIT_PLAN_ANALYSIS（使用共享的EDIT_PLAN_ANALYSIS）
  /** 审核修改计划分析 */
  EDIT_PLAN_ANALYSIS = "edit_plan_analysis",
  /** 路线图修正 */
  ROADMAP_EDIT = "roadmap_edit",
  /** 人工审核 */
  HUMAN_REVIEW = "human_review",
  /** 内容生成已入队 */
  CONTENT_GENERATION_QUEUED = "content_generation_queued",
  /** 内容生成（包含教程、资源、测验） */
  CONTENT_GENERATION = "content_generation",
  /** 资源推荐（已废弃，由content_generation统一处理） */
  RESOURCE_RECOMMENDATION = "resource_recommendation",
  /** 测验生成（已废弃，由content_generation统一处理） */
  QUIZ_GENERATION = "quiz_generation",
  /** 收尾中 */
  // ✅ 移除：FINALIZING（不需要此步骤）
  /** 已完成 */
  COMPLETED = "completed",
  /** 失败 */
  FAILED = "failed",
}

/**
 * WorkflowStep 类型 (Union Type)
 */
export type WorkflowStepType = "init" | "queued" | "starting" | "intent_analysis" | "curriculum_design" | "structure_validation" | "validation_edit_plan_analysis" | "edit_plan_analysis" | "roadmap_edit" | "human_review" | "content_generation_queued" | "content_generation" | "resource_recommendation" | "quiz_generation" | "finalizing" | "completed" | "failed";

/**
 * WorkflowStep 类型守卫
 */
export function isWorkflowStep(value: any): value is WorkflowStepType {
  return [
    "init",
    "queued",
    "starting",
    "intent_analysis",
    "curriculum_design",
    "structure_validation",
    "validation_edit_plan_analysis",
    "edit_plan_analysis",
    "roadmap_edit",
    "human_review",
    "content_generation_queued",
    "content_generation",
    "resource_recommendation",
    "quiz_generation",
    "finalizing",
    "completed",
    "failed",
  ].includes(value);
}

/**
 * WorkflowStep 标签映射
 */
export const WorkflowStepLabels: Record<WorkflowStepType, string> = {
  "init": "初始化",
  "queued": "已入队",
  "starting": "启动中",
  "intent_analysis": "需求分析",
  "curriculum_design": "课程设计",
  "structure_validation": "结构验证",
  "validation_edit_plan_analysis": "验证修改计划分析",
  "edit_plan_analysis": "审核修改计划分析",
  "roadmap_edit": "路线图修正",
  "human_review": "人工审核",
  "content_generation_queued": "内容生成已入队",
  "content_generation": "内容生成（包含教程、资源、测验）",
  "resource_recommendation": "资源推荐（已废弃，由content_generation统一处理）",
  "quiz_generation": "测验生成（已废弃，由content_generation统一处理）",
  "finalizing": "收尾中",
  "completed": "已完成",
  "failed": "失败",
};

