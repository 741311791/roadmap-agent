/**
 * Generated Models
 * TODO: 应该从后端 OpenAPI schema 自动生成
 * 目前使用手动定义的类型
 */

// Re-export existing models
export * from './models/LearningPreferences';
export * from './models/UserRequest';
export * from './models/ModifyContentRequest';
export * from './models/RegenerateContentRequest';
export * from './models/RetryFailedRequest';
export * from './models/ValidationError';
export * from './models/HTTPValidationError';

// ============================================================
// Domain Models (from backend/app/models/domain.py)
// ============================================================

/**
 * 概念内容状态
 */
export type ContentStatus = 'pending' | 'generating' | 'completed' | 'failed';

/**
 * 难度等级
 */
export type DifficultyLevel = 'easy' | 'medium' | 'hard';

/**
 * 概念 - 第三层：知识点
 */
export interface Concept {
  concept_id: string;
  name: string;
  description: string;
  estimated_hours: number;
  prerequisites: string[];
  difficulty: DifficultyLevel;
  keywords: string[];
  
  // 教程内容引用
  content_status: ContentStatus;
  content_ref?: string | null;
  content_version: string;
  content_summary?: string | null;
  tutorial_id?: string | null;
  
  // 资源推荐引用
  resources_status: ContentStatus;
  resources_id?: string | null;
  resources_count: number;
  
  // 测验引用
  quiz_status: ContentStatus;
  quiz_id?: string | null;
  quiz_question_count: number;
  
  // 整体状态（来自 concept_metadata 表）
  // pending: 未开始 | generating: 生成中 | completed: 全部完成 | partial_failed: 部分失败
  overall_status?: ContentStatus | 'partial_failed';
}

/**
 * 模块 - 第二层
 */
export interface Module {
  module_id: string;
  name: string;
  description: string;
  learning_objectives?: string[];
  concepts: Concept[];
}

/**
 * 阶段 - 第一层
 */
export interface Stage {
  stage_id: string;
  name: string;
  description: string;
  order: number;
  modules: Module[];
}

/**
 * 完整的路线图框架
 */
export interface RoadmapFramework {
  roadmap_id: string;
  title: string;
  stages: Stage[];
  total_estimated_hours: number;
  recommended_completion_weeks: number;
  
  // 可选的元数据字段（用于列表展示）
  created_at?: string;
  total_concepts?: number;
  completed_concepts?: number;
  topic?: string;
  status?: 'draft' | 'completed' | 'archived';
}

/**
 * 路线图详情（包含元数据）
 */
export interface RoadmapDetail {
  roadmap_id: string;
  user_id: string;
  learning_goal: string;
  created_at: string;
  updated_at: string;
  framework: RoadmapFramework;
}

/**
 * 教程章节
 */
export interface TutorialSection {
  section_id: string;
  title: string;
  content: string;
  order: number;
  estimated_minutes: number;
  code_examples?: CodeExample[];
}

/**
 * 代码示例
 */
export interface CodeExample {
  language: string;
  code: string;
  description?: string;
  runnable: boolean;
}

/**
 * 完整教程
 */
export interface Tutorial {
  tutorial_id: string;
  concept_id: string;
  roadmap_id: string;
  title: string;
  summary: string;
  difficulty: DifficultyLevel;
  estimated_time_minutes: number;
  sections: TutorialSection[];
  prerequisites: string[];
  learning_objectives: string[];
  key_takeaways: string[];
  next_steps: string[];
  created_at: string;
  updated_at: string;
  version: string;
}

/**
 * 资源类型
 */
export type ResourceType = 
  | 'official_doc'
  | 'video'
  | 'article'
  | 'interactive'
  | 'book'
  | 'course'
  | 'tool'
  | 'community';

/**
 * 资源推荐
 */
export interface ResourceRecommendation {
  resource_id: string;
  title: string;
  url: string;
  type: ResourceType;
  description: string;
  difficulty: DifficultyLevel;
  estimated_time_minutes?: number;
  is_free: boolean;
  rating?: number;
  relevance_score?: number;
  author?: string;
  platform?: string;
}

/**
 * 资源推荐响应
 */
export interface ResourceRecommendations {
  concept_id: string;
  roadmap_id: string;
  resources: ResourceRecommendation[];
  created_at: string;
  metadata_id: string;
}

/**
 * 测验题目类型
 * 仅支持：单选、多选、判断三种类型
 */
export type QuizQuestionType = 'single_choice' | 'multiple_choice' | 'true_false';

/**
 * 测验选项
 */
export interface QuizOption {
  option_id: string;
  text: string;
  is_correct: boolean;
  explanation?: string;
}

/**
 * 测验题目
 */
export interface QuizQuestion {
  question_id: string;
  type: QuizQuestionType;
  question: string;
  options?: QuizOption[];
  correct_answer?: string;
  explanation: string;
  difficulty: DifficultyLevel;
  points: number;
  code_snippet?: string;
}

/**
 * 完整测验
 */
export interface Quiz {
  quiz_id: string;
  concept_id: string;
  roadmap_id: string;
  title: string;
  description: string;
  questions: QuizQuestion[];
  total_points: number;
  passing_score: number;
  estimated_time_minutes: number;
  created_at: string;
  version: string;
}

/**
 * 任务状态
 */
export type TaskStatus = 
  | 'pending'
  | 'processing'
  | 'running'
  | 'completed'
  | 'partial_failure'
  | 'failed'
  | 'human_review_pending'
  | 'human_review_required'
  | 'approved'
  | 'rejected';

/**
 * 任务状态响应
 */
export interface TaskStatusResponse {
  task_id: string;
  status: TaskStatus;
  progress: number;
  current_step?: string;
  roadmap_id?: string;
  result?: any;
  error?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

/**
 * 完整的教程内容（包含状态）
 */
export interface TutorialWithContent extends Tutorial {
  status: 'completed' | 'generating' | 'failed';
}

