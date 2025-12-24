/**
 * 用户相关的 Zod Schema 定义
 */

import { z } from 'zod';

/**
 * 学习偏好 Schema
 */
export const LearningPreferencesSchema = z.object({
  learning_goal: z.string().min(10, '学习目标至少 10 个字符').max(500, '学习目标最多 500 个字符'),
  current_level: z.enum(['beginner', 'intermediate', 'advanced']),
  time_commitment: z.string().optional(),
  preferred_resources: z.array(z.string()).optional(),
  learning_style: z.string().optional(),
});

/**
 * 用户请求 Schema
 */
export const UserRequestSchema = z.object({
  user_id: z.string(),
  preferences: LearningPreferencesSchema,
  skip_validation: z.boolean().optional(),
  skip_human_review: z.boolean().optional(),
});

/**
 * 用户画像 Schema
 */
export const UserProfileSchema = z.object({
  user_id: z.string(),
  username: z.string().optional(),
  email: z.string().email().optional(),
  created_at: z.string().datetime().optional(),
  updated_at: z.string().datetime().optional(),
  
  // 学习偏好
  preferences: LearningPreferencesSchema.optional(),
  
  // 学习统计
  stats: z.object({
    total_roadmaps: z.number().int().nonnegative(),
    completed_concepts: z.number().int().nonnegative(),
    total_hours_spent: z.number().nonnegative(),
  }).optional(),
});

/**
 * 类型推导
 */
export type LearningPreferences = z.infer<typeof LearningPreferencesSchema>;
export type UserRequest = z.infer<typeof UserRequestSchema>;
export type UserProfile = z.infer<typeof UserProfileSchema>;

/**
 * 验证函数
 */
export function validateUserRequest(data: unknown): UserRequest {
  return UserRequestSchema.parse(data);
}

export function validateUserProfile(data: unknown): UserProfile {
  return UserProfileSchema.parse(data);
}

/**
 * 安全验证函数
 */
export function safeValidateUserRequest(data: unknown) {
  return UserRequestSchema.safeParse(data);
}

export function safeValidateUserProfile(data: unknown) {
  return UserProfileSchema.safeParse(data);
}

/**
 * 表单验证 Schema (用于 react-hook-form)
 */
export const CreateRoadmapFormSchema = z.object({
  learning_goal: z.string().min(10, '学习目标至少 10 个字符').max(500, '学习目标最多 500 个字符'),
  current_level: z.enum(['beginner', 'intermediate', 'advanced'], {
    message: '请选择当前水平',
  }),
  time_commitment: z.string().optional(),
  preferred_resources: z.array(z.string()).optional().default([]),
  learning_style: z.string().optional(),
});

export type CreateRoadmapFormData = z.infer<typeof CreateRoadmapFormSchema>;
