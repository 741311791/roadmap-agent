/**
 * Generated Models - 重新导出
 * 
 * ⚠️ 此文件已重构为仅重新导出生成的类型
 * 手动定义的类型已移除，请使用自动生成的类型
 * 
 * 使用方式:
 * import { TaskStatus, WorkflowStep } from '@/types/generated/constants';
 * import { GenerateRoadmapResponse } from '@/types/generated';
 */

// ============================================================
// 重新导出所有生成的核心模型
// ============================================================
// 注意：这些导出与下面的手动定义的业务模型不冲突

// 用户相关
export type { UserProfileRequest } from './models/UserProfileRequest';
export type { UserProfileResponse } from './models/UserProfileResponse';
export type { UserRequest } from './models/UserRequest';
export type { UserRead } from './models/UserRead';
export type { UserUpdate } from './models/UserUpdate';
export type { TechStackItem } from './models/TechStackItem';

// 路线图相关
export type { FeaturedRoadmapItem } from './models/FeaturedRoadmapItem';
export type { FeaturedRoadmapsResponse } from './models/FeaturedRoadmapsResponse';
export type { RoadmapHistoryItem } from './models/RoadmapHistoryItem';
export type { RoadmapHistoryResponse } from './models/RoadmapHistoryResponse';
export type { GenerateRoadmapResponse } from './models/GenerateRoadmapResponse';
export type { IntentAnalysisResponse } from './models/IntentAnalysisResponse';
export type { EditRecordResponse } from './models/EditRecordResponse';
export type { EditRecordListResponse } from './models/EditRecordListResponse';
export type { ValidationRecordResponse } from './models/ValidationRecordResponse';
export type { ValidationRecordListResponse } from './models/ValidationRecordListResponse';
export type { RoadmapConceptsStatusResponse } from './models/RoadmapConceptsStatusResponse';
export type { CoverImageResponse } from './models/CoverImageResponse';

// 任务相关
export type { TaskStatusDetailResponse } from './models/TaskStatusDetailResponse';
export type { TaskListResponse } from './models/TaskListResponse';
export type { TaskItemResponse } from './models/TaskItemResponse';
export type { TaskRetryStatus } from './models/TaskRetryStatus';
export type { ApprovalRequest } from './models/ApprovalRequest';
export type { ApprovalResponse } from './models/ApprovalResponse';
export type { CancelTaskResponse } from './models/CancelTaskResponse';
export type { RetryResponse } from './models/RetryResponse';
export type { RetryRequest } from './models/RetryRequest';
export type { ExecutionLogResponse } from './models/ExecutionLogResponse';
export type { ExecutionLogListResponse } from './models/ExecutionLogListResponse';
export type { TraceSummaryResponse } from './models/TraceSummaryResponse';

// 内容相关
export type { TutorialDetailResponse } from './models/TutorialDetailResponse';
export type { TutorialVersionListResponse } from './models/TutorialVersionListResponse';
export type { TutorialItemResponse } from './models/TutorialItemResponse';
export type { ResourcesResponse } from './models/ResourcesResponse';
export type { QuizResponse } from './models/QuizResponse';
export type { QuestionResponse } from './models/QuestionResponse';
export type { QuizAttemptResponse } from './models/QuizAttemptResponse';
export type { QuizAttemptCreate } from './models/QuizAttemptCreate';
export type { ModifyContentRequest } from './models/ModifyContentRequest';
export type { RetryContentRequest } from './models/RetryContentRequest';
export type { RetryContentResponse } from './models/RetryContentResponse';

// 内容修改类型别名（所有内容类型使用统一的 ModifyContentRequest）
export type { ModifyContentRequest as ModifyTutorialRequest } from './models/ModifyContentRequest';
export type { ModifyContentRequest as ModifyResourcesRequest } from './models/ModifyContentRequest';
export type { ModifyContentRequest as ModifyQuizRequest } from './models/ModifyContentRequest';

// 修改响应类型（根据实际返回类型定义别名）
export type { TutorialDetailResponse as ModifyTutorialResponse } from './models/TutorialDetailResponse';

// 学习相关
export type { AssessmentResponse } from './models/AssessmentResponse';
export type { CustomAssessmentResponse } from './models/CustomAssessmentResponse';
export type { EvaluationResult } from './models/EvaluationResult';
export type { ConceptProgressResponse } from './models/ConceptProgressResponse';
export type { ConceptProgressUpdate } from './models/ConceptProgressUpdate';
export type { ConceptStatusResponse } from './models/ConceptStatusResponse';
export type { LearningPreferences } from './models/LearningPreferences';
// ⚠️ 以下类型尚未实现，暂时注释
// export type { LearningNoteCreate } from './models/LearningNoteCreate';
// export type { LearningNoteResponse } from './models/LearningNoteResponse';
// export type { LearningNoteUpdate } from './models/LearningNoteUpdate';

// 聊天相关
// ⚠️ 以下类型尚未实现，暂时注释
// export type { ChatMessageResponse } from './models/ChatMessageResponse';
// export type { ChatSessionResponse } from './models/ChatSessionResponse';
// export type { ChatModificationRequest } from './models/ChatModificationRequest';
// export type { ChatStreamRequest } from './models/ChatStreamRequest';

// 认证相关
export type { BearerResponse } from './models/BearerResponse';
export type { BlacklistStatsResponse } from './models/BlacklistStatsResponse';
export type { LogoutResponse } from './models/LogoutResponse';

// 管理员相关
export type { WaitlistJoinRequest } from './models/WaitlistJoinRequest';
export type { WaitlistJoinResponse } from './models/WaitlistJoinResponse';
export type { WaitlistResponse } from './models/WaitlistResponse';
export type { WaitlistUserInfo } from './models/WaitlistUserInfo';
export type { WaitlistInviteItem } from './models/WaitlistInviteItem';
export type { WaitlistInviteListResponse } from './models/WaitlistInviteListResponse';
export type { InviteUserRequest } from './models/InviteUserRequest';
export type { InviteUserResponse } from './models/InviteUserResponse';
export type { TavilyAPIKeyInfo } from './models/TavilyAPIKeyInfo';
export type { TavilyAPIKeyListResponse } from './models/TavilyAPIKeyListResponse';
export type { CeleryTaskInfo } from './models/CeleryTaskInfo';
export type { CeleryTaskListResponse } from './models/CeleryTaskListResponse';
export type { CeleryWorkerInfo } from './models/CeleryWorkerInfo';
export type { CeleryWorkerListResponse } from './models/CeleryWorkerListResponse';
export type { CeleryOverview } from './models/CeleryOverview';

// 通用
export type { ResponseModel } from './models/ResponseModel';
export type { ErrorModel } from './models/ErrorModel';
export type { ValidationError } from './models/ValidationError';
export type { HTTPValidationError } from './models/HTTPValidationError';

// ============================================================
// 向后兼容: 保留一些常用的类型别名
// ============================================================

// 导入枚举类型用于业务模型定义
import type { TaskStatusType, WorkflowStepType, ContentStatusType } from './constants';

// 注意：使用枚举时，请直接从 '@/types/generated/constants' 导入
// - TaskStatus (枚举), TaskStatusType (字符串联合类型)
// - WorkflowStep (枚举), WorkflowStepType (字符串联合类型)
// - ContentStatus (枚举), ContentStatusType (字符串联合类型)

// ============================================================
// 业务领域模型 (从生成的类型中重新导出)
// ============================================================

// 这些类型应该从后端 OpenAPI Schema 自动生成
// 如果缺失，请运行: npm run generate:types

/**
 * 难度等级
 */
export type DifficultyLevel = 'easy' | 'medium' | 'hard';

/**
 * 概念 - 第三层：知识点
 * 
 * ⚠️ 此类型应该从后端 Schema 生成
 * 目前作为临时定义保留
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
  content_status: ContentStatusType;
  content_ref?: string | null;
  content_version: string;
  content_summary?: string | null;
  tutorial_id?: string | null;
  
  // 资源推荐引用
  resources_status: ContentStatusType;
  resources_id?: string | null;
  resources_count: number;
  
  // 测验引用
  quiz_status: ContentStatusType;
  quiz_id?: string | null;
  quiz_questions_count: number;
}

/**
 * 模块 - 第二层：主题模块
 */
export interface Module {
  module_id: string;
  name: string;
  description: string;
  concepts: Concept[];
}

/**
 * 阶段 - 第一层：学习阶段
 */
export interface Stage {
  stage_id: string;
  name: string;
  description: string;
  order: number;
  modules: Module[];
}

/**
 * 路线图框架
 */
export interface RoadmapFramework {
  roadmap_id: string;
  title: string;
  stages: Stage[];
  total_estimated_hours: number;
  recommended_completion_weeks: number;
}

/**
 * 教程章节
 */
export interface TutorialSection {
  section_id: string;
  title: string;
  content: string;
  content_type: 'theory' | 'example' | 'exercise' | 'quiz';
  estimated_minutes: number;
}

/**
 * 教程
 */
export interface Tutorial {
  tutorial_id: string;
  concept_id: string;
  title: string;
  summary: string;
  sections: TutorialSection[];
  recommended_resources: Array<{ title: string; url: string; type: string }>;
  exercises: string[];
  estimated_completion_time: number;
  estimated_time_minutes?: number; // 别名字段
  version: string;
  generated_at: string;
  storage_url?: string | null;
  difficulty?: 'beginner' | 'intermediate' | 'advanced' | 'easy' | 'medium' | 'hard';
  prerequisites?: string[];
  // 扩展字段（从 Markdown 内容解析）
  learning_objectives?: string[];
  key_takeaways?: string[];
  next_steps?: string[];
}

/**
 * 资源
 */
export interface Resource {
  title: string;
  url: string;
  type: 'article' | 'video' | 'book' | 'course' | 'documentation' | 'tool';
  description: string;
  relevance_score: number;
  language?: string;
}

/**
 * 资源推荐输出
 */
export interface ResourceRecommendationOutput {
  id: string;
  concept_id: string;
  resources: Resource[];
  search_queries_used: string[];
  generated_at: string;
}

/**
 * 测验问题
 */
export interface QuizQuestion {
  question_id: string;
  question_type: 'single_choice' | 'multiple_choice' | 'true_false' | 'fill_blank';
  question: string;
  options: string[];
  correct_answer: number[];
  explanation: string;
  difficulty: DifficultyLevel;
  points: number;
}

/**
 * 测验
 */
export interface Quiz {
  quiz_id: string;
  concept_id: string;
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
 * 任务状态响应
 * 
 * ⚠️ 此类型应该从后端 Schema 生成
 * 请使用 TaskStatusDetailResponse
 */
export interface TaskStatusResponse {
  task_id: string;
  status: TaskStatusType;
  progress: number;
  current_step?: WorkflowStepType;
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
