/**
 * 自动生成的常量类型定义
 * 
 * 从后端 backend/app/models/constants.py 生成
 * 
 * ⚠️ WARNING: 请勿手动修改此文件
 * Run `npm run generate:constants` 重新生成
 * 
 * Generated at: 2026-02-09T13:14:00.149Z
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
 *     
 *     核心步骤：
 *     - 主路节点：INTENT_ANALYSIS → CURRICULUM_DESIGN → STRUCTURE_VALIDATION → HUMAN_REVIEW → CONTENT_GENERATION
 *     - 共享编辑节点：EDIT_PLAN_ANALYSIS、ROADMAP_EDIT（由edit_source区分来源）
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
  /** 人工审核 */
  HUMAN_REVIEW = "human_review",
  /** 编辑计划分析（共享） */
  EDIT_PLAN_ANALYSIS = "edit_plan_analysis",
  /** 路线图修正（共享） */
  ROADMAP_EDIT = "roadmap_edit",
  /** 内容生成已入队 */
  CONTENT_GENERATION_QUEUED = "content_generation_queued",
  /** 内容生成（包含教程、资源、测验） */
  CONTENT_GENERATION = "content_generation",
  /** 已完成 */
  COMPLETED = "completed",
  /** 失败 */
  FAILED = "failed",
}

/**
 * WorkflowStep 类型 (Union Type)
 */
export type WorkflowStepType = "init" | "queued" | "starting" | "intent_analysis" | "curriculum_design" | "structure_validation" | "human_review" | "edit_plan_analysis" | "roadmap_edit" | "content_generation_queued" | "content_generation" | "completed" | "failed";

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
    "human_review",
    "edit_plan_analysis",
    "roadmap_edit",
    "content_generation_queued",
    "content_generation",
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
  "human_review": "人工审核",
  "edit_plan_analysis": "编辑计划分析（共享）",
  "roadmap_edit": "路线图修正（共享）",
  "content_generation_queued": "内容生成已入队",
  "content_generation": "内容生成（包含教程、资源、测验）",
  "completed": "已完成",
  "failed": "失败",
};

