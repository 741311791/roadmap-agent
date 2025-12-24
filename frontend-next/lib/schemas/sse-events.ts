/**
 * SSE 事件相关的 Zod Schema 定义
 * 
 * 与后端 FRONTEND_API_GUIDE.md 完全对齐
 */

import { z } from 'zod';
import { WorkflowStep } from '@/lib/constants/status';

/**
 * 基础 SSE 事件 Schema
 */
export const BaseSSEEventSchema = z.object({
  type: z.string(),
  timestamp: z.string().datetime(),
});

/**
 * 进度事件 Schema
 */
export const ProgressEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('progress'),
  task_id: z.string(),
  current_step: z.nativeEnum(WorkflowStep),
  message: z.string(),
  data: z.object({
    roadmap_id: z.string().optional(),
    stages_count: z.number().optional(),
    total_concepts: z.number().optional(),
  }).catchall(z.unknown()).optional(),
});

/**
 * 步骤完成事件 Schema
 */
export const StepCompleteEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('step_complete'),
  task_id: z.string(),
  step: z.nativeEnum(WorkflowStep),
  result: z.record(z.string(), z.unknown()).optional(),
});

/**
 * 完成事件 Schema
 */
export const CompleteEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('complete'),
  task_id: z.string(),
  roadmap_id: z.string(),
  status: z.enum(['completed', 'partial_failure']),
  tutorials_count: z.number().optional(),
  failed_count: z.number().optional(),
});

/**
 * 错误事件 Schema (路线图生成场景)
 */
export const ErrorEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('roadmap_error'),
  task_id: z.string(),
  error: z.string(),
  step: z.nativeEnum(WorkflowStep).optional(),
});

/**
 * 通用错误事件 Schema
 */
export const GenericErrorEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('error'),
  message: z.string(),
  details: z.string().optional(),
});

/**
 * 流式 chunk 事件 Schema (用于路线图生成过程)
 */
export const ChunkEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('chunk'),
  agent: z.string(),
  content: z.string(),
});

/**
 * 教程生成开始事件 Schema
 */
export const TutorialsStartEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('tutorials_start'),
  total_count: z.number(),
  batch_size: z.number(),
});

/**
 * 批次开始事件 Schema
 */
export const BatchStartEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('batch_start'),
  batch_index: z.number(),
  total_batches: z.number(),
});

/**
 * 教程开始事件 Schema
 */
export const TutorialStartEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('tutorial_start'),
  concept_name: z.string(),
  concept_id: z.string(),
});

/**
 * 教程完成事件 Schema
 */
export const TutorialCompleteEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('tutorial_complete'),
  concept_id: z.string(),
});

/**
 * 教程错误事件 Schema
 */
export const TutorialErrorEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('tutorial_error'),
  concept_id: z.string(),
  error: z.string(),
});

/**
 * 批次完成事件 Schema
 */
export const BatchCompleteEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('batch_complete'),
  batch_index: z.number(),
  progress: z.number(),
});

/**
 * 教程全部完成事件 Schema
 */
export const TutorialsDoneEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('tutorials_done'),
  summary: z.string(),
});

/**
 * 生成完成事件 Schema (done)
 */
export const DoneEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('done'),
  roadmap_id: z.string(),
  summary: z.string(),
});

/**
 * 路线图生成事件联合类型 Schema
 */
export const RoadmapGenerationEventSchema = z.discriminatedUnion('type', [
  ProgressEventSchema,
  StepCompleteEventSchema,
  CompleteEventSchema,
  ErrorEventSchema,
  ChunkEventSchema,
  TutorialsStartEventSchema,
  BatchStartEventSchema,
  TutorialStartEventSchema,
  TutorialCompleteEventSchema,
  TutorialErrorEventSchema,
  BatchCompleteEventSchema,
  TutorialsDoneEventSchema,
  DoneEventSchema,
  GenericErrorEventSchema,
]);

/**
 * 聊天修改事件类型
 */

/**
 * 分析中事件 Schema
 */
export const AnalyzingEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('analyzing'),
  message: z.string(),
});

/**
 * 意图事件 Schema
 */
export const IntentsEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('intents'),
  intents: z.array(z.object({
    modification_type: z.string(),
    target_id: z.string(),
    target_name: z.string(),
    specific_requirements: z.array(z.string()),
    priority: z.enum(['high', 'medium', 'low']),
  })),
  needs_clarification: z.boolean(),
  clarification_questions: z.array(z.string()).optional(),
});

/**
 * 修改中事件 Schema
 */
export const ModifyingEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('modifying'),
  target_type: z.string(),
  target_id: z.string(),
  target_name: z.string(),
  message: z.string(),
});

/**
 * Agent 进度事件 Schema
 */
export const AgentProgressEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('agent_progress'),
  agent: z.string(),
  step: z.string(),
  details: z.string().optional(),
});

/**
 * 结果事件 Schema
 */
export const ResultEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('result'),
  target_type: z.string(),
  target_id: z.string(),
  target_name: z.string(),
  success: z.boolean(),
  modification_type: z.string().optional(),
  modification_summary: z.string().optional(),
  new_version: z.number().optional(),
  error_message: z.string().optional(),
});

/**
 * 修改完成事件 Schema
 */
export const ModificationDoneEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('done'),
  overall_success: z.boolean(),
  partial_success: z.boolean(),
  summary: z.string(),
  successful_count: z.number(),
  failed_count: z.number(),
});

/**
 * 修改错误事件 Schema
 */
export const ModificationErrorEventSchema = BaseSSEEventSchema.extend({
  type: z.literal('modification_error'),
  message: z.string(),
  details: z.string().optional(),
});

/**
 * 聊天修改事件联合类型 Schema
 */
export const ChatModificationEventSchema = z.discriminatedUnion('type', [
  AnalyzingEventSchema,
  IntentsEventSchema,
  ModifyingEventSchema,
  AgentProgressEventSchema,
  ResultEventSchema,
  ModificationDoneEventSchema,
  ModificationErrorEventSchema,
  GenericErrorEventSchema,
]);

/**
 * 类型推导
 */
export type BaseSSEEvent = z.infer<typeof BaseSSEEventSchema>;
export type ProgressEvent = z.infer<typeof ProgressEventSchema>;
export type StepCompleteEvent = z.infer<typeof StepCompleteEventSchema>;
export type CompleteEvent = z.infer<typeof CompleteEventSchema>;
export type ErrorEvent = z.infer<typeof ErrorEventSchema>;
export type ChunkEvent = z.infer<typeof ChunkEventSchema>;
export type TutorialsStartEvent = z.infer<typeof TutorialsStartEventSchema>;
export type BatchStartEvent = z.infer<typeof BatchStartEventSchema>;
export type TutorialStartEvent = z.infer<typeof TutorialStartEventSchema>;
export type TutorialCompleteEvent = z.infer<typeof TutorialCompleteEventSchema>;
export type TutorialErrorEvent = z.infer<typeof TutorialErrorEventSchema>;
export type BatchCompleteEvent = z.infer<typeof BatchCompleteEventSchema>;
export type TutorialsDoneEvent = z.infer<typeof TutorialsDoneEventSchema>;
export type DoneEvent = z.infer<typeof DoneEventSchema>;
export type RoadmapGenerationEvent = z.infer<typeof RoadmapGenerationEventSchema>;

export type AnalyzingEvent = z.infer<typeof AnalyzingEventSchema>;
export type IntentsEvent = z.infer<typeof IntentsEventSchema>;
export type ModifyingEvent = z.infer<typeof ModifyingEventSchema>;
export type AgentProgressEvent = z.infer<typeof AgentProgressEventSchema>;
export type ResultEvent = z.infer<typeof ResultEventSchema>;
export type ModificationDoneEvent = z.infer<typeof ModificationDoneEventSchema>;
export type ModificationErrorEvent = z.infer<typeof ModificationErrorEventSchema>;
export type GenericErrorEvent = z.infer<typeof GenericErrorEventSchema>;
export type ChatModificationEvent = z.infer<typeof ChatModificationEventSchema>;

/**
 * 验证函数
 */
export function validateSSEEvent(data: unknown, eventType?: string): RoadmapGenerationEvent {
  return RoadmapGenerationEventSchema.parse(data);
}

export function validateChatEvent(data: unknown, eventType?: string): ChatModificationEvent {
  return ChatModificationEventSchema.parse(data);
}

/**
 * 安全验证函数
 */
export function safeValidateSSEEvent(data: unknown) {
  return RoadmapGenerationEventSchema.safeParse(data);
}

export function safeValidateChatEvent(data: unknown) {
  return ChatModificationEventSchema.safeParse(data);
}

/**
 * 类型守卫函数
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

export function isModificationErrorEvent(event: BaseSSEEvent): event is ModificationErrorEvent {
  return event.type === 'modification_error';
}
