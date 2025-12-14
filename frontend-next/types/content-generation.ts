/**
 * Content Generation 相关类型定义
 * 
 * 用于任务详情页中的内容生成状态展示
 */

/**
 * 内容生成状态
 */
export type ContentGenerationStatus = 'pending' | 'generating' | 'completed' | 'failed';

/**
 * 内容类型（三种）
 */
export type ContentType = 'tutorial' | 'resources' | 'quiz';

/**
 * 单个内容类型的状态信息
 */
export interface ContentTypeStatus {
  status: ContentGenerationStatus;
  error?: string;
  // Tutorial 特有字段
  tutorial_id?: string;
  content_url?: string;
  // Resources 特有字段
  resources_id?: string;
  resources_count?: number;
  // Quiz 特有字段
  quiz_id?: string;
  questions_count?: number;
}

/**
 * Concept 级别的内容生成状态
 */
export interface ConceptGenerationStatus {
  concept_id: string;
  concept_name: string;
  
  // 三种内容类型的状态
  tutorial: ContentTypeStatus;
  resources: ContentTypeStatus;
  quiz: ContentTypeStatus;
}

/**
 * Module 级别的内容生成状态
 */
export interface ModuleGenerationStatus {
  module_id: string;
  module_name: string;
  concepts: ConceptGenerationStatus[];
  
  // 统计信息
  total_concepts: number;
  completed_concepts: number;
  failed_concepts: number;
}

/**
 * Stage 级别的内容生成状态
 */
export interface StageGenerationStatus {
  stage_id: string;
  stage_name: string;
  modules: ModuleGenerationStatus[];
  
  // 统计信息
  total_concepts: number;
  completed_concepts: number;
  failed_concepts: number;
}

/**
 * 完整的内容生成概览
 */
export interface ContentGenerationOverview {
  stages: StageGenerationStatus[];
  last_updated: Date;
  
  // 全局统计
  total_concepts: number;
  completed_concepts: number;
  failed_concepts: number;
  progress_percentage: number;
}

/**
 * 执行日志条目（从现有类型扩展）
 */
export interface ExecutionLog {
  id: string;
  task_id: string;
  level: string;
  category: string;
  step: string | null;
  agent_name: string | null;
  message: string;
  details: any;
  duration_ms: number | null;
  created_at: string;
}

/**
 * 日志中的内容生成事件类型
 * 
 * 后端实际发送的日志类型：
 * - content_generation_start: 开始生成某个概念的内容
 * - concept_completed: 某个概念的所有内容（tutorial + resources + quiz）生成成功
 * - content_generation_failed: 某个概念生成失败
 */
export type ContentLogType =
  | 'content_generation_start'
  | 'concept_completed'
  | 'content_generation_failed';
