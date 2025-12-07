/**
 * Server-Sent Events Types
 * 
 * 与后端 FRONTEND_API_GUIDE.md 完全对齐
 * 最后更新: 2025-12-06
 * 
 * ⚠️ 注意: 
 * 1. 这些类型定义与 lib/schemas/sse-events.ts 中的 Zod Schema 保持一致
 * 2. 如需修改,请同时更新两处
 */

import type { RoadmapFramework } from '../generated/models';
import type { WorkflowStep, TaskStatus, ContentStatus } from '@/lib/constants/status';

// ============================================================
// 基础 SSE 事件
// ============================================================

export interface BaseSSEEvent {
  type: string;
  timestamp: string;  // ISO 8601 格式
}

// ============================================================
// 路线图生成 SSE 事件（与后端 FRONTEND_API_GUIDE.md 完全对齐）
// ============================================================

/**
 * 进度更新事件
 */
export interface ProgressEvent extends BaseSSEEvent {
  type: 'progress';
  task_id: string;
  current_step: WorkflowStep;
  message: string;
  data?: {
    roadmap_id?: string;
    stages_count?: number;
    total_concepts?: number;
    [key: string]: unknown;
  };
}

/**
 * 步骤完成事件
 */
export interface StepCompleteEvent extends BaseSSEEvent {
  type: 'step_complete';
  task_id: string;
  step: WorkflowStep;
  result?: {
    roadmap?: RoadmapFramework;
    [key: string]: unknown;
  };
}

/**
 * 任务完成事件
 */
export interface CompleteEvent extends BaseSSEEvent {
  type: 'complete';
  task_id: string;
  roadmap_id: string;
  status: 'completed' | 'partial_failure';
  tutorials_count?: number;
  failed_count?: number;
}

/**
 * 错误事件（路线图生成场景）
 */
export interface ErrorEvent extends BaseSSEEvent {
  type: 'roadmap_error';
  task_id: string;
  error: string;
  step?: WorkflowStep;
}

/**
 * 路线图生成事件联合类型
 */
export type RoadmapGenerationEvent =
  | ProgressEvent
  | StepCompleteEvent
  | CompleteEvent
  | ErrorEvent;

// ============================================================
// WebSocket 事件（路线图生成场景）
// ============================================================

/**
 * 连接成功确认
 */
export interface ConnectedEvent extends BaseSSEEvent {
  type: 'connected';
  task_id: string;
  message: string;
}

/**
 * 当前状态事件（仅在 include_history=true 时发送）
 */
export interface CurrentStatusEvent extends BaseSSEEvent {
  type: 'current_status';
  task_id: string;
  status: TaskStatus;
  current_step: WorkflowStep;
  roadmap_id?: string;
  created_at?: string;
  updated_at?: string;
}

/**
 * 人工审核请求事件
 */
export interface HumanReviewRequiredEvent extends BaseSSEEvent {
  type: 'human_review_required';
  task_id: string;
  roadmap_id: string;
  roadmap_title: string;
  stages_count: number;
  message: string;
}

/**
 * 任务完成事件（WebSocket）
 */
export interface CompletedEvent extends BaseSSEEvent {
  type: 'completed';
  task_id: string;
  roadmap_id: string;
  tutorials_count?: number;
  failed_count?: number;
  message: string;
}

/**
 * 任务失败事件（WebSocket）
 */
export interface FailedEvent extends BaseSSEEvent {
  type: 'failed';
  task_id: string;
  error: string;
  step?: WorkflowStep;
  message: string;
}

/**
 * Concept 开始生成事件
 */
export interface ConceptStartEvent extends BaseSSEEvent {
  type: 'concept_start';
  task_id: string;
  concept_id: string;
  concept_name: string;
  progress: {
    current: number;
    total: number;
    percentage: number;
  };
  message: string;
}

/**
 * Concept 生成完成事件
 */
export interface ConceptCompleteEvent extends BaseSSEEvent {
  type: 'concept_complete';
  task_id: string;
  concept_id: string;
  concept_name: string;
  data?: {
    tutorial_id?: string;
    content_url?: string;
    [key: string]: unknown;
  };
  message: string;
}

/**
 * Concept 生成失败事件
 */
export interface ConceptFailedEvent extends BaseSSEEvent {
  type: 'concept_failed';
  task_id: string;
  concept_id: string;
  concept_name: string;
  error: string;
  message: string;
}

/**
 * 批次处理开始事件
 */
export interface BatchStartEvent extends BaseSSEEvent {
  type: 'batch_start';
  task_id: string;
  batch_index: number;
  batch_size: number;
  total_batches: number;
  concept_ids: string[];
  message: string;
}

/**
 * 批次处理完成事件
 */
export interface BatchCompleteEvent extends BaseSSEEvent {
  type: 'batch_complete';
  task_id: string;
  batch_index: number;
  total_batches: number;
  progress: {
    completed: number;
    failed: number;
    total: number;
    percentage: number;
  };
  message: string;
}

/**
 * 连接即将关闭事件
 */
export interface ClosingEvent extends BaseSSEEvent {
  type: 'closing';
  task_id: string;
  reason: string;
  message: string;
}

/**
 * WebSocket 错误事件
 */
export interface WSErrorEvent extends BaseSSEEvent {
  type: 'ws_error';
  task_id: string;
  message: string;
}

/**
 * WebSocket 事件联合类型
 */
export type WebSocketEvent =
  | ConnectedEvent
  | CurrentStatusEvent
  | ProgressEvent
  | HumanReviewRequiredEvent
  | ConceptStartEvent
  | ConceptCompleteEvent
  | ConceptFailedEvent
  | BatchStartEvent
  | BatchCompleteEvent
  | CompletedEvent
  | FailedEvent
  | ClosingEvent
  | WSErrorEvent;

// ============================================================
// 聊天修改 SSE 事件（AI 聊天场景）
// ============================================================

/**
 * 分析中事件
 */
export interface AnalyzingEvent extends BaseSSEEvent {
  type: 'analyzing';
  message: string;
}

/**
 * 意图分析结果事件
 */
export interface IntentsEvent extends BaseSSEEvent {
  type: 'intents';
  intents: Array<{
    modification_type: string;
    target_id: string;
    target_name: string;
    specific_requirements: string[];
    priority: 'high' | 'medium' | 'low';
  }>;
  needs_clarification: boolean;
  clarification_questions?: string[];
}

/**
 * 修改中事件
 */
export interface ModifyingEvent extends BaseSSEEvent {
  type: 'modifying';
  target_type: string;
  target_id: string;
  target_name: string;
  message: string;
}

/**
 * 修改结果事件
 */
export interface ResultEvent extends BaseSSEEvent {
  type: 'result';
  target_type: string;
  target_id: string;
  target_name: string;
  success: boolean;
  modification_summary?: string;
  new_version?: number;
  error_message?: string;
}

/**
 * 修改完成事件
 */
export interface ModificationDoneEvent extends BaseSSEEvent {
  type: 'done';
  overall_success: boolean;
  partial_success: boolean;
  summary: string;
  successful_count: number;
  failed_count: number;
}

/**
 * 修改错误事件
 */
export interface ModificationErrorEvent extends BaseSSEEvent {
  type: 'modification_error';
  message: string;
  details?: string;
}

/**
 * 聊天修改事件联合类型
 */
export type ChatModificationEvent =
  | AnalyzingEvent
  | IntentsEvent
  | ModifyingEvent
  | ResultEvent
  | ModificationDoneEvent
  | ModificationErrorEvent;

// ============================================================
// 类型守卫函数
// ============================================================

/**
 * SSE 事件类型守卫
 */
export function isProgressEvent(event: BaseSSEEvent): event is ProgressEvent {
  return event.type === 'progress';
}

export function isStepCompleteEvent(event: BaseSSEEvent): event is StepCompleteEvent {
  return event.type === 'step_complete';
}

export function isCompleteEvent(event: BaseSSEEvent): event is CompleteEvent {
  return event.type === 'complete';
}

export function isErrorEvent(event: BaseSSEEvent): event is ErrorEvent {
  return event.type === 'roadmap_error';
}

/**
 * WebSocket 事件类型守卫
 */
export function isConnectedEvent(event: BaseSSEEvent): event is ConnectedEvent {
  return event.type === 'connected';
}

export function isCurrentStatusEvent(event: BaseSSEEvent): event is CurrentStatusEvent {
  return event.type === 'current_status';
}

export function isHumanReviewRequiredEvent(event: BaseSSEEvent): event is HumanReviewRequiredEvent {
  return event.type === 'human_review_required';
}

export function isConceptStartEvent(event: BaseSSEEvent): event is ConceptStartEvent {
  return event.type === 'concept_start';
}

export function isConceptCompleteEvent(event: BaseSSEEvent): event is ConceptCompleteEvent {
  return event.type === 'concept_complete';
}

export function isConceptFailedEvent(event: BaseSSEEvent): event is ConceptFailedEvent {
  return event.type === 'concept_failed';
}

export function isBatchStartEvent(event: BaseSSEEvent): event is BatchStartEvent {
  return event.type === 'batch_start';
}

export function isBatchCompleteEvent(event: BaseSSEEvent): event is BatchCompleteEvent {
  return event.type === 'batch_complete';
}

/**
 * 聊天修改事件类型守卫
 */
export function isAnalyzingEvent(event: BaseSSEEvent): event is AnalyzingEvent {
  return event.type === 'analyzing';
}

export function isIntentsEvent(event: BaseSSEEvent): event is IntentsEvent {
  return event.type === 'intents';
}

export function isModifyingEvent(event: BaseSSEEvent): event is ModifyingEvent {
  return event.type === 'modifying';
}

export function isResultEvent(event: BaseSSEEvent): event is ResultEvent {
  return event.type === 'result';
}

export function isModificationDoneEvent(event: BaseSSEEvent): event is ModificationDoneEvent {
  return event.type === 'done';
}

export function isWSErrorEvent(event: BaseSSEEvent): event is WSErrorEvent {
  return event.type === 'ws_error';
}

export function isModificationErrorEvent(event: BaseSSEEvent): event is ModificationErrorEvent {
  return event.type === 'modification_error';
}

// ============================================================
// SSE Event Handler Types
// ============================================================

export type SSEEventHandler<T extends BaseSSEEvent> = (event: T) => void;

export interface SSEHandlers<T extends BaseSSEEvent> {
  onEvent: SSEEventHandler<T>;
  onError?: (error: Error) => void;
  onComplete?: () => void;
}

