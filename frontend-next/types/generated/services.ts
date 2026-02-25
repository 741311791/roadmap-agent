/**
 * Generated Service Types
 * API 响应类型定义
 * 
 * ⚠️ 此文件已重构：重复的类型已移至自动生成的 models
 * 请从 '@/types/generated' 直接导入这些类型
 */

import type { 
  RoadmapFramework, 
  Tutorial, 
  ResourceRecommendationOutput,
  Quiz,
  QuizQuestion,
  TutorialWithContent,
} from './models';

// Re-export TutorialWithContent to avoid duplication
export type { TutorialWithContent };

/**
 * 路线图列表响应
 */
export interface RoadmapListResponse {
  roadmaps: Array<{
    roadmap_id: string;
    title: string;
    created_at: string;
    total_concepts: number;
    completed_concepts: number;
    topic?: string;
    status: 'draft' | 'completed' | 'archived';
  }>;
  total: number;
}

/**
 * 教程响应
 */
export interface TutorialResponse {
  tutorial: Tutorial;
  status: 'completed' | 'generating' | 'failed';
}

/**
 * ⚠️ 注意：ResourcesResponse 已从 models 自动生成
 * 请从 '@/types/generated' 直接导入
 */

/**
 * 用户个人资料（非自动生成）
 * 
 * ⚠️ 注意：以下类型已从 models 自动生成，请从 '@/types/generated' 导入：
 * - QuizResponse
 * - UserProfileRequest
 * - UserProfileResponse
 * - ModifyTutorialRequest
 * - ModifyTutorialResponse
 * - ModifyResourcesRequest
 * - ModifyQuizRequest
 */
export interface UserProfile {
  user_id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  created_at: string;
  updated_at: string;
}

