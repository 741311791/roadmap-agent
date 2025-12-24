/**
 * 路线图相关的 Zod Schema 定义
 * 
 * 用于运行时验证从 API 返回的数据
 */

import { z } from 'zod';
import { ContentStatus } from '@/lib/constants/status';

/**
 * 概念 Schema
 */
export const ConceptSchema = z.object({
  concept_id: z.string(),
  concept_number: z.number().int().positive(),
  title: z.string(),
  description: z.string(),
  key_points: z.array(z.string()),
  prerequisites: z.array(z.string()),
  estimated_time: z.string(),
  
  // 内容状态
  tutorial_status: z.nativeEnum(ContentStatus),
  resources_status: z.nativeEnum(ContentStatus),
  quiz_status: z.nativeEnum(ContentStatus),
});

/**
 * 模块 Schema
 */
export const ModuleSchema = z.object({
  module_id: z.string(),
  module_number: z.number().int().positive(),
  title: z.string(),
  description: z.string(),
  learning_objectives: z.array(z.string()),
  concepts: z.array(ConceptSchema),
});

/**
 * 阶段 Schema
 */
export const StageSchema = z.object({
  stage_id: z.string(),
  stage_number: z.number().int().positive(),
  title: z.string(),
  description: z.string(),
  estimated_duration: z.string(),
  modules: z.array(ModuleSchema),
});

/**
 * 路线图框架 Schema
 */
export const RoadmapFrameworkSchema = z.object({
  roadmap_id: z.string(),
  title: z.string(),
  stages: z.array(StageSchema),
  total_estimated_hours: z.number().positive().optional(),
  recommended_completion_weeks: z.number().positive().optional(),
});

/**
 * 路线图详情 Schema
 */
export const RoadmapDetailSchema = z.object({
  roadmap_id: z.string(),
  user_id: z.string(),
  learning_goal: z.string(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  framework: RoadmapFrameworkSchema,
});

/**
 * 路线图摘要 Schema (用于列表)
 */
export const RoadmapSummarySchema = z.object({
  roadmap_id: z.string(),
  task_id: z.string(),
  learning_goal: z.string(),
  status: z.string(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

/**
 * 路线图列表响应 Schema
 */
export const RoadmapListResponseSchema = z.object({
  total: z.number().int().nonnegative(),
  items: z.array(RoadmapSummarySchema),
});

/**
 * 类型推导
 */
export type Concept = z.infer<typeof ConceptSchema>;
export type Module = z.infer<typeof ModuleSchema>;
export type Stage = z.infer<typeof StageSchema>;
export type RoadmapFramework = z.infer<typeof RoadmapFrameworkSchema>;
export type RoadmapDetail = z.infer<typeof RoadmapDetailSchema>;
export type RoadmapSummary = z.infer<typeof RoadmapSummarySchema>;
export type RoadmapListResponse = z.infer<typeof RoadmapListResponseSchema>;

/**
 * 验证函数
 */
export function validateRoadmapFramework(data: unknown): RoadmapFramework {
  return RoadmapFrameworkSchema.parse(data);
}

export function validateRoadmapDetail(data: unknown): RoadmapDetail {
  return RoadmapDetailSchema.parse(data);
}

export function validateRoadmapList(data: unknown): RoadmapListResponse {
  return RoadmapListResponseSchema.parse(data);
}

/**
 * 安全验证函数 (不抛出错误)
 */
export function safeValidateRoadmapFramework(data: unknown) {
  return RoadmapFrameworkSchema.safeParse(data);
}

export function safeValidateRoadmapDetail(data: unknown) {
  return RoadmapDetailSchema.safeParse(data);
}

export function safeValidateRoadmapList(data: unknown) {
  return RoadmapListResponseSchema.safeParse(data);
}
