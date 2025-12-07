/**
 * Generated Service Types
 * API 响应类型定义
 */

import type { 
  RoadmapFramework, 
  Tutorial, 
  ResourceRecommendations, 
  ResourceRecommendation,
  Quiz,
  QuizQuestion,
} from './models';

/**
 * 生成路线图响应
 */
export interface GenerateRoadmapResponse {
  task_id: string;
  roadmap_id: string;
  framework: RoadmapFramework;
}

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
 * 完整的教程内容（包含状态）
 */
export interface TutorialWithContent extends Tutorial {
  status: 'completed' | 'generating' | 'failed';
}

/**
 * 资源推荐响应
 */
export interface ResourcesResponse {
  resources: ResourceRecommendation[];  // 直接是数组
  resources_count: number;
  status: 'completed' | 'generating' | 'failed';
}

/**
 * 测验响应
 */
export interface QuizResponse {
  quiz: Quiz;
  questions: QuizQuestion[];
  total_questions: number;
  status: 'completed' | 'generating' | 'failed';
}

/**
 * 用户个人资料
 */
export interface UserProfile {
  user_id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  created_at: string;
  updated_at: string;
}

/**
 * 用户个人资料请求
 */
export interface UserProfileRequest {
  name?: string;
  avatar_url?: string;
}

/**
 * 用户个人资料响应
 */
export interface UserProfileResponse {
  user: UserProfile;
}

/**
 * 修改教程请求
 */
export interface ModifyTutorialRequest {
  concept_id: string;
  roadmap_id: string;
  modification: string;
}

/**
 * 修改教程响应
 */
export interface ModifyTutorialResponse {
  tutorial: Tutorial;
  message: string;
}

/**
 * 修改资源推荐请求
 */
export interface ModifyResourcesRequest {
  concept_id: string;
  roadmap_id: string;
  modification: string;
}

/**
 * 修改测验请求
 */
export interface ModifyQuizRequest {
  concept_id: string;
  roadmap_id: string;
  modification: string;
}

