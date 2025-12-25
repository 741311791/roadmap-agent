/**
 * API Endpoints
 * 
 * Type-safe API endpoint definitions matching backend routes
 */

import { apiClient } from './client';
import type {
  RoadmapFramework,
  UserRequest,
  LearningPreferences,
} from '@/types/generated/models';
import type {
  QuizResponse,
  ResourcesResponse,
} from '@/types/generated/services';

// ============================================================
// Helper Functions
// ============================================================

/**
 * URL编码概念ID
 * 
 * 概念ID可能包含特殊字符（如冒号），需要在URL中进行编码
 */
function encodeConceptId(conceptId: string): string {
  return encodeURIComponent(conceptId);
}

// ============================================================
// Roadmap Endpoints
// ============================================================

export interface TaskStatus {
  task_id: string;
  status: 'pending' | 'processing' | 'completed' | 'partial_failure' | 'failed' | 'human_review_pending' | 'human_review_required';
  current_step?: string;
  progress?: number;
  error_message?: string;
  roadmap_id?: string;
  roadmap_data?: RoadmapFramework;
}

export interface GenerateResponse {
  task_id: string;
  status: string;
  message: string;
}

/**
 * Generate a new roadmap (async background task)
 * 
 * This is the non-streaming version that returns a task_id.
 * Use WebSocket to subscribe to task progress updates.
 * 
 * @param request - User request with learning preferences
 * @returns Task info with task_id for tracking
 */
export async function generateRoadmapAsync(
  request: UserRequest
): Promise<GenerateResponse> {
  const response = await apiClient.post<GenerateResponse>(
    '/roadmaps/generate',
    request
  );
  return response.data;
}


/**
 * Get roadmap generation status
 */
export async function getRoadmapStatus(taskId: string): Promise<TaskStatus> {
  const response = await apiClient.get<TaskStatus>(
    `/roadmaps/${taskId}/status`
  );
  return response.data;
}

/**
 * Get complete roadmap by ID
 */
export async function getRoadmap(roadmapId: string): Promise<RoadmapFramework> {
  const response = await apiClient.get<RoadmapFramework>(
    `/roadmaps/${roadmapId}`
  );
  return response.data;
}

/**
 * Get roadmap's active task
 * 
 * 查询路线图是否有正在进行的任务
 */
export async function getRoadmapActiveTask(roadmapId: string): Promise<{
  has_active_task: boolean;
  task_id: string | null;
  status: string | null;
  current_step: string | null;
  task_type?: string | null;
  concept_id?: string | null;
  content_type?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}> {
  const response = await apiClient.get(
    `/roadmaps/${roadmapId}/active-task`
  );
  return response.data;
}

/**
 * 快速检查路线图状态（检测僵尸状态）
 * 
 * 检测逻辑：
 * 1. 获取路线图的 task_id
 * 2. 检查任务是否还在运行
 * 3. 如果任务不在运行，但概念状态为 pending/generating，则为僵尸状态
 * 
 * @param roadmapId - 路线图 ID
 * @returns 状态检查结果，包含僵尸状态的概念列表
 */
export async function checkRoadmapStatusQuick(roadmapId: string): Promise<{
  roadmap_id: string;
  has_active_task: boolean;
  task_status: string | null;
  active_tasks?: Array<{
    task_id: string;
    concept_id: string;
    content_type: 'tutorial' | 'resources' | 'quiz';
    status: string;
  }>;
  stale_concepts: Array<{
    concept_id: string;
    concept_name: string;
    content_type: 'tutorial' | 'resources' | 'quiz';
    current_status: 'pending' | 'generating';
  }>;
}> {
  const response = await apiClient.get(
    `/roadmaps/${roadmapId}/status-check`
  );
  return response.data;
}

/**
 * Approve/reject roadmap framework (human-in-the-loop)
 */
export async function approveRoadmap(
  taskId: string,
  approved: boolean,
  feedback?: string
): Promise<{ status: string }> {
  const response = await apiClient.post(`/roadmaps/${taskId}/approve`, null, {
    params: { approved, feedback },
  });
  return response.data;
}

// ============================================================
// Retry Failed Content (断点续传)
// ============================================================

export interface RetryFailedRequest {
  user_id: string;
  preferences: LearningPreferences;
  content_types: ('tutorial' | 'resources' | 'quiz')[];
}

export interface RetryFailedResponse {
  task_id?: string;
  roadmap_id: string;
  status: 'processing' | 'no_failed_items';
  items_to_retry?: {
    tutorial?: number;
    resources?: number;
    quiz?: number;
  };
  total_items?: number;
  message: string;
  failed_counts?: {
    tutorial: number;
    resources: number;
    quiz: number;
  };
}

/**
 * Retry failed content generation (断点续传)
 * 
 * Only re-runs content that failed, not the entire generation.
 * Each content type (tutorial, resources, quiz) is tracked independently.
 * 
 * @param roadmapId - The roadmap ID to retry failed content for
 * @param request - The retry request with user preferences and content types
 * @returns Task info for WebSocket subscription
 */
export async function retryFailedContent(
  roadmapId: string,
  request: RetryFailedRequest
): Promise<RetryFailedResponse> {
  const response = await apiClient.post<RetryFailedResponse>(
    `/roadmaps/${roadmapId}/retry-failed`,
    request
  );
  return response.data;
}

/**
 * Get failed content statistics for a roadmap
 */
export async function getFailedContentStats(
  roadmapId: string
): Promise<{
  tutorial: number;
  resources: number;
  quiz: number;
  total: number;
}> {
  // This can be derived from the roadmap data locally
  // or we can add a dedicated backend endpoint
  const roadmap = await getRoadmap(roadmapId);
  
  let tutorialFailed = 0;
  let resourcesFailed = 0;
  let quizFailed = 0;
  
  for (const stage of roadmap.stages || []) {
    for (const module of stage.modules || []) {
      for (const concept of module.concepts || []) {
        if ((concept as any).content_status === 'failed') tutorialFailed++;
        if ((concept as any).resources_status === 'failed') resourcesFailed++;
        if ((concept as any).quiz_status === 'failed') quizFailed++;
      }
    }
  }
  
  return {
    tutorial: tutorialFailed,
    resources: resourcesFailed,
    quiz: quizFailed,
    total: tutorialFailed + resourcesFailed + quizFailed,
  };
}

// ============================================================
// 单概念内容重试 API (Single Concept Retry)
// ============================================================

export interface RetryContentRequest {
  preferences: LearningPreferences;
}

export interface RetryContentResponse {
  success: boolean;
  concept_id: string;
  content_type: 'tutorial' | 'resources' | 'quiz';
  message: string;
  data?: Record<string, unknown>;
}

/**
 * 重试单个概念的教程生成
 * 
 * @param roadmapId - 路线图 ID
 * @param conceptId - 概念 ID
 * @param request - 包含用户学习偏好的请求
 * @returns 重试结果
 */
export async function retryTutorial(
  roadmapId: string,
  conceptId: string,
  request: RetryContentRequest
): Promise<RetryContentResponse> {
  const response = await apiClient.post<RetryContentResponse>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/tutorial/retry`,
    request
  );
  return response.data;
}

/**
 * 重试单个概念的资源推荐生成
 * 
 * @param roadmapId - 路线图 ID
 * @param conceptId - 概念 ID
 * @param request - 包含用户学习偏好的请求
 * @returns 重试结果
 */
export async function retryResources(
  roadmapId: string,
  conceptId: string,
  request: RetryContentRequest
): Promise<RetryContentResponse> {
  const response = await apiClient.post<RetryContentResponse>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/resources/retry`,
    request
  );
  return response.data;
}

/**
 * 重试单个概念的测验生成
 * 
 * @param roadmapId - 路线图 ID
 * @param conceptId - 概念 ID
 * @param request - 包含用户学习偏好的请求
 * @returns 重试结果
 */
export async function retryQuiz(
  roadmapId: string,
  conceptId: string,
  request: RetryContentRequest
): Promise<RetryContentResponse> {
  const response = await apiClient.post<RetryContentResponse>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/quiz/retry`,
    request
  );
  return response.data;
}

// ============================================================
// Tutorial Endpoints
// ============================================================

export interface TutorialContent {
  tutorial_id: string;
  concept_id: string;
  title: string;
  summary: string;
  content?: string;
  content_url?: string;
  content_version?: number;
  estimated_completion_time?: number;
  version: number;
  generated_at: string;
}

/**
 * Get latest tutorial for a concept
 */
export async function getLatestTutorial(
  roadmapId: string,
  conceptId: string
): Promise<TutorialContent> {
  const response = await apiClient.get<TutorialContent>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/tutorials/latest`
  );
  return response.data;
}

/**
 * Get specific tutorial version
 */
export async function getTutorialVersion(
  roadmapId: string,
  conceptId: string,
  version: number
): Promise<TutorialContent> {
  const response = await apiClient.get<TutorialContent>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/tutorials/v${version}`
  );
  return response.data;
}

/**
 * Regenerate tutorial for a concept
 */
export async function regenerateTutorial(
  roadmapId: string,
  conceptId: string,
  request: {
    user_id: string;
    preferences: LearningPreferences;
  }
): Promise<{
  tutorial_id: string;
  content_version: number;
  content_url: string;
  content_status: string;
  generated_at: string;
}> {
  const response = await apiClient.post(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/regenerate`,
    request
  );
  return response.data;
}

// ============================================================
// Resource Endpoints
// ============================================================

export interface Resource {
  title: string;
  url: string;
  type: string;
  description: string;
  relevance_score: number;
}

export interface ResourceList {
  concept_id: string;
  resources: Resource[];
}

/**
 * Get resources for a concept
 */
export async function getResources(
  roadmapId: string,
  conceptId: string
): Promise<ResourceList> {
  // Note: This endpoint might need to be added to backend
  const response = await apiClient.get<ResourceList>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/resources`
  );
  return response.data;
}

/**
 * Regenerate resources for a concept
 */
export async function regenerateResources(
  roadmapId: string,
  conceptId: string,
  preferences: LearningPreferences
): Promise<{ task_id: string }> {
  const response = await apiClient.post(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/resources/regenerate`,
    { user_preferences: preferences }
  );
  return response.data;
}

// ============================================================
// Quiz Endpoints
// ============================================================

export interface QuizQuestion {
  question_id: string;
  question_type: string;
  question: string;
  options: string[];
  correct_answer: number[];
  explanation: string;
  difficulty: string;
}

export interface Quiz {
  quiz_id: string;
  concept_id: string;
  questions: QuizQuestion[];
  total_questions: number;
}

/**
 * Get quiz for a concept
 */
export async function getQuiz(
  roadmapId: string,
  conceptId: string
): Promise<Quiz> {
  // Note: This endpoint might need to be added to backend
  const response = await apiClient.get<Quiz>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/quiz`
  );
  return response.data;
}

/**
 * Regenerate quiz for a concept
 */
export async function regenerateQuiz(
  roadmapId: string,
  conceptId: string,
  preferences: LearningPreferences
): Promise<{ task_id: string }> {
  const response = await apiClient.post(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/quiz/regenerate`,
    { user_preferences: preferences }
  );
  return response.data;
}

// ============================================================
// Streaming Endpoints
// ============================================================

import { SSEManager, createGenerationStream, createChatModificationStream } from './sse';
import type { BaseSSEEvent, RoadmapGenerationEvent, ChatModificationEvent } from '@/types/custom/sse';

/**
 * Generate roadmap with streaming (framework only, no tutorials)
 */
export async function generateRoadmapStream(
  request: UserRequest,
  handlers: {
    onEvent: (event: RoadmapGenerationEvent) => void;
    onComplete?: () => void;
    onError?: (error: Error) => void;
  }
): Promise<SSEManager<BaseSSEEvent>> {
  const manager = new SSEManager<BaseSSEEvent>({
    url: `/api/v1/roadmaps/generate-stream`,
    handlers: {
      onEvent: (event) => handlers.onEvent(event as RoadmapGenerationEvent),
      onComplete: handlers.onComplete,
      onError: handlers.onError,
    },
    body: request,
  });

  await manager.connectWithPost();
  return manager;
}

/**
 * Generate complete roadmap with streaming (includes tutorials)
 */
export async function generateFullRoadmapStream(
  request: UserRequest,
  handlers: {
    onEvent: (event: RoadmapGenerationEvent) => void;
    onComplete?: () => void;
    onError?: (error: Error) => void;
  }
): Promise<SSEManager<BaseSSEEvent>> {
  const manager = new SSEManager<BaseSSEEvent>({
    url: `/api/v1/roadmaps/generate-full-stream`,
    handlers: {
      onEvent: (event) => handlers.onEvent(event as RoadmapGenerationEvent),
      onComplete: handlers.onComplete,
      onError: handlers.onError,
    },
    body: request,
  });

  await manager.connectWithPost();
  return manager;
}

/**
 * Chat-based modification with streaming
 */
export async function chatModificationStream(
  roadmapId: string,
  request: {
    user_id: string;
    user_message: string;
    preferences: LearningPreferences;
    context?: { concept_id?: string };
  },
  handlers: {
    onEvent: (event: ChatModificationEvent) => void;
    onComplete?: () => void;
    onError?: (error: Error) => void;
  }
): Promise<SSEManager<BaseSSEEvent>> {
  const manager = new SSEManager<BaseSSEEvent>({
    url: `/api/v1/roadmaps/${roadmapId}/chat-stream`,
    handlers: {
      onEvent: (event) => handlers.onEvent(event as ChatModificationEvent),
      onComplete: handlers.onComplete,
      onError: handlers.onError,
    },
    body: request,
  });

  await manager.connectWithPost();
  return manager;
}

// ============================================================
// Tutorial Content Download
// ============================================================

/**
 * Download tutorial content via backend proxy (solves CORS issue)
 * 
 * 前端不再直接访问 R2/S3 URL，而是通过后端代理下载
 * 这样避免了 CORS 跨域问题
 */
export async function downloadTutorialContent(
  roadmapId: string,
  conceptId: string
): Promise<string> {
  try {
    const response = await apiClient.get(
      `/roadmaps/${roadmapId}/concepts/${conceptId}/tutorials/latest/content`,
      {
        responseType: 'text',
      }
    );
    return response.data;
  } catch (error) {
    console.error('Error downloading tutorial content:', error);
    throw error;
  }
}

// ============================================================
// Resources and Quiz by Concept ID
// ============================================================

/**
 * Get resources for a specific concept
 * Note: This endpoint needs to be implemented in the backend
 */
export async function getResourcesByConceptId(
  roadmapId: string,
  conceptId: string
): Promise<ResourceList> {
  try {
    const response = await apiClient.get<ResourceList>(
      `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/resources`
    );
    return response.data;
  } catch (error) {
    // If endpoint doesn't exist yet, return empty
    console.warn('Resources endpoint not implemented yet');
    return {
      concept_id: conceptId,
      resources: [],
    };
  }
}

/**
 * Get quiz for a specific concept
 * Note: This endpoint needs to be implemented in the backend
 */
export async function getQuizByConceptId(
  roadmapId: string,
  conceptId: string
): Promise<Quiz> {
  try {
    const response = await apiClient.get<Quiz>(
      `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/quiz`
    );
    return response.data;
  } catch (error) {
    // If endpoint doesn't exist yet, return empty
    console.warn('Quiz endpoint not implemented yet');
    return {
      quiz_id: `${conceptId}-quiz`,
      concept_id: conceptId,
      questions: [],
      total_questions: 0,
    };
  }
}

// ============================================================
// Tutorial Version Management
// ============================================================

/**
 * Get all tutorial versions for a concept
 */
export async function getTutorialVersions(
  roadmapId: string,
  conceptId: string
): Promise<{
  roadmap_id: string;
  concept_id: string;
  total_versions: number;
  tutorials: Array<{
    tutorial_id: string;
    title: string;
    summary: string;
    content_url: string;
    content_version: number;
    is_latest: boolean;
    content_status: string;
    generated_at: string;
  }>;
}> {
  const response = await apiClient.get(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/tutorials`
  );
  return response.data;
}

/**
 * Get tutorial by specific version
 */
export async function getTutorialByVersion(
  roadmapId: string,
  conceptId: string,
  version: number
): Promise<TutorialContent> {
  const response = await apiClient.get<TutorialContent>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/tutorials/v${version}`
  );
  return response.data;
}

// ============================================================
// Modification Endpoints
// ============================================================

export interface ModifyRequest {
  modification_requirements: string[];
  user_preferences: LearningPreferences;
}

export interface ModifyResponse {
  success: boolean;
  modification_summary: string;
  new_version?: number;
}

/**
 * Modify tutorial content
 */
export async function modifyTutorial(
  roadmapId: string,
  conceptId: string,
  request: ModifyRequest
): Promise<ModifyResponse> {
  const response = await apiClient.post<ModifyResponse>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/tutorial/modify`,
    request
  );
  return response.data;
}

// ============================================================
// Quiz & Resources Endpoints
// ============================================================

export interface QuizQuestionLocal {
  question_id: string;
  question_type: 'single_choice' | 'multiple_choice' | 'true_false' | 'fill_blank';
  question: string;
  options: string[];
  correct_answer: number[];
  explanation: string;
  difficulty: 'easy' | 'medium' | 'hard';
}

export interface QuizResponseLocal {
  roadmap_id: string;
  concept_id: string;
  quiz_id: string;
  questions: QuizQuestionLocal[];
  total_questions: number;
  easy_count: number;
  medium_count: number;
  hard_count: number;
  generated_at: string | null;
}

export interface ResourceLocal {
  title: string;
  url: string;
  type: 'article' | 'video' | 'book' | 'course' | 'documentation' | 'tool';
  description: string;
  relevance_score: number;
}

export interface ResourcesResponseLocal {
  roadmap_id: string;
  concept_id: string;
  resources_id: string;
  resources: ResourceLocal[];
  resources_count: number;
  search_queries_used: string[];
  generated_at: string | null;
}

/**
 * Get quiz for a concept
 */
export async function getConceptQuiz(
  roadmapId: string,
  conceptId: string
): Promise<QuizResponse> {
  const response = await apiClient.get<QuizResponse>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/quiz`
  );
  return response.data;
}

/**
 * Get resources for a concept
 */
export async function getConceptResources(
  roadmapId: string,
  conceptId: string
): Promise<ResourcesResponse> {
  const response = await apiClient.get<ResourcesResponse>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/resources`
  );
  return response.data;
}

// ============================================================
// Edit History Endpoints (Version Control)
// ============================================================

/**
 * 编辑历史版本数据
 */
export interface EditHistoryVersion {
  version: number;
  framework_data: RoadmapFramework;
  created_at: string;
  edit_round: number;
  modification_summary: string;
  modified_node_ids: string[];
}

/**
 * 完整编辑历史响应
 */
export interface EditHistoryResponse {
  versions: EditHistoryVersion[];
  current_version: number;
}

/**
 * 获取任务的完整编辑历史版本链
 * 
 * 将编辑记录按时间顺序串联成完整的版本链，
 * 每个版本包含完整的框架数据和相对于上一版本的修改节点列表。
 * 
 * @param taskId - 任务 ID
 * @param roadmapId - 路线图 ID
 * @returns 完整的版本链数据
 */
export async function getFullEditHistory(
  taskId: string,
  roadmapId: string
): Promise<EditHistoryResponse> {
  const response = await apiClient.get<EditHistoryResponse>(
    `/tasks/${taskId}/edit/history-full`,
    {
      params: { roadmap_id: roadmapId }
    }
  );
  return response.data;
}

// ============================================================
// Resources and Quiz Modification
// ============================================================

export async function modifyResources(
  roadmapId: string,
  conceptId: string,
  request: ModifyRequest
): Promise<ModifyResponse> {
  const response = await apiClient.post<ModifyResponse>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/resources/modify`,
    request
  );
  return response.data;
}

/**
 * Modify quiz
 */
export async function modifyQuiz(
  roadmapId: string,
  conceptId: string,
  request: ModifyRequest
): Promise<ModifyResponse> {
  const response = await apiClient.post<ModifyResponse>(
    `/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/quiz/modify`,
    request
  );
  return response.data;
}

// ============================================================
// User Profile Endpoints
// ============================================================

export interface TechStackItem {
  technology: string;
  proficiency: 'beginner' | 'intermediate' | 'expert';
  capability_analysis?: any; // 能力分析结果（可选）
}

export interface UserProfileData {
  user_id: string;
  industry?: string | null;
  current_role?: string | null;
  tech_stack: TechStackItem[];
  primary_language: string;
  secondary_language?: string | null;
  weekly_commitment_hours: number;
  learning_style: ('visual' | 'text' | 'audio' | 'hands_on')[];
  ai_personalization: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface UserProfileRequest {
  industry?: string | null;
  current_role?: string | null;
  tech_stack: TechStackItem[];
  primary_language: string;
  secondary_language?: string | null;
  weekly_commitment_hours: number;
  learning_style: string[];
  ai_personalization: boolean;
}

/**
 * Get user profile
 */
export async function getUserProfile(userId: string): Promise<UserProfileData> {
  const response = await apiClient.get<UserProfileData>(
    `/users/${userId}/profile`
  );
  return response.data;
}

/**
 * Save or update user profile
 */
export async function saveUserProfile(
  userId: string,
  data: UserProfileRequest
): Promise<UserProfileData> {
  const response = await apiClient.put<UserProfileData>(
    `/users/${userId}/profile`,
    data
  );
  return response.data;
}

// ============================================================
// User Roadmaps History
// ============================================================

export interface StageSummary {
  name: string;
  description?: string | null;
  order: number;
}

export interface RoadmapHistoryItem {
  roadmap_id: string;
  title: string;
  created_at: string;
  total_concepts: number;
  completed_concepts: number;
  topic?: string | null;
  status?: string | null;
  stages?: StageSummary[] | null;
  // 新增字段：用于支持未完成路线图的恢复
  task_id?: string | null;
  task_status?: string | null;  // processing, pending, human_review_pending 等
  current_step?: string | null;  // intent_analysis, curriculum_design 等
  // 软删除相关字段
  deleted_at?: string | null;
  deleted_by?: string | null;
}

export interface RoadmapHistoryResponse {
  roadmaps: RoadmapHistoryItem[];
  total: number;
  in_progress_count?: number;  // 进行中的任务数量
}

/**
 * Get user's roadmap history
 */
export async function getUserRoadmaps(
  userId: string,
  limit: number = 50,
  offset: number = 0
): Promise<RoadmapHistoryResponse> {
  const response = await apiClient.get<RoadmapHistoryResponse>(
    `/users/${userId}/roadmaps`,
    {
      params: { limit, offset },
    }
  );
  return response.data;
}

/**
 * 获取精选路线图列表
 * 
 * 从配置的Featured User (admin@example.com) 获取已完成的路线图，
 * 用于首页Featured Roadmaps模块展示。
 * 
 * @param limit - 返回数量限制（默认50）
 * @param offset - 分页偏移（默认0）
 * @returns 精选路线图列表
 */
export async function getFeaturedRoadmaps(
  limit: number = 50,
  offset: number = 0
): Promise<RoadmapHistoryResponse> {
  const response = await apiClient.get<RoadmapHistoryResponse>(
    `/featured/roadmaps`,
    {
      params: { limit, offset },
    }
  );
  return response.data;
}

// ============================================================
// 路线图删除与回收站相关接口
// ============================================================

/**
 * 软删除路线图（移至回收站）
 */
export async function deleteRoadmap(
  roadmapId: string,
  userId: string
): Promise<{ success: boolean; roadmap_id: string; deleted_at: string | null }> {
  const response = await apiClient.delete(
    `/roadmaps/${roadmapId}`,
    {
      params: { user_id: userId },
    }
  );
  return response.data;
}

/**
 * 从回收站恢复路线图
 */
export async function restoreRoadmap(
  roadmapId: string,
  userId: string
): Promise<{ success: boolean; roadmap_id: string }> {
  const response = await apiClient.post(
    `/roadmaps/${roadmapId}/restore`,
    null,
    {
      params: { user_id: userId },
    }
  );
  return response.data;
}

/**
 * 永久删除路线图（不可恢复）
 */
export async function permanentDeleteRoadmap(
  roadmapId: string,
  userId: string
): Promise<{ success: boolean; roadmap_id: string }> {
  const response = await apiClient.delete(
    `/roadmaps/${roadmapId}/permanent`,
    {
      params: { user_id: userId },
    }
  );
  return response.data;
}

/**
 * 获取回收站中的路线图列表
 */
export async function getDeletedRoadmaps(
  userId: string,
  limit: number = 50,
  offset: number = 0
): Promise<RoadmapHistoryResponse> {
  const response = await apiClient.get<RoadmapHistoryResponse>(
    `/users/${userId}/roadmaps/trash`,
    {
      params: { limit, offset },
    }
  );
  return response.data;
}

// ============================================================
// 任务列表相关接口
// ============================================================

/**
 * 任务列表项
 */
export interface TaskItem {
  task_id: string;
  status: string;
  current_step: string;
  title: string;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  roadmap_id?: string | null;
}

/**
 * 任务列表响应
 */
export interface TaskListResponse {
  tasks: TaskItem[];
  total: number;
  pending_count: number;
  processing_count: number;
  completed_count: number;
  failed_count: number;
}

/**
 * 获取用户的任务列表
 */
export async function getUserTasks(
  userId: string,
  status?: string,
  taskType: string = 'creation',
  limit: number = 50,
  offset: number = 0
): Promise<TaskListResponse> {
  const response = await apiClient.get<TaskListResponse>(
    `/users/${userId}/tasks`,
    {
      params: { status, task_type: taskType, limit, offset },
    }
  );
  return response.data;
}

/**
 * 重试失败的任务（智能重试）
 * 
 * 自动选择两种重试策略之一：
 * 1. Checkpoint 恢复：任务在早期阶段失败，从 LangGraph checkpoint 恢复
 * 2. 内容重试：内容生成阶段部分失败，只重新生成失败的 Concept 内容
 */
export interface RetryTaskResponse {
  success: boolean;
  recovery_type: 'checkpoint' | 'content_retry';
  
  // Checkpoint 恢复时返回
  task_id?: string;
  checkpoint_step?: string;
  
  // 内容重试时返回
  new_task_id?: string;
  old_task_id?: string;
  items_to_retry?: Record<string, number>;
  total_items?: number;
  
  // 通用字段
  roadmap_id: string;
  status: string;
  message: string;
}

export async function retryTask(
  taskId: string,
  userId: string,
  forceCheckpoint: boolean = false
): Promise<RetryTaskResponse> {
  const response = await apiClient.post(
    `/tasks/${taskId}/retry`,
    null,
    {
      params: { 
        user_id: userId,
        force_checkpoint: forceCheckpoint,
      },
    }
  );
  return response.data;
}

/**
 * 删除任务
 * 
 * 根据任务格式自动判断删除方式：
 * - 对于进行中的任务（task-{uuid}格式），物理删除任务记录
 * - 对于完成的路线图，软删除（可恢复）
 */
export async function deleteTask(
  taskId: string,
  userId: string
): Promise<{ success: boolean; roadmap_id: string; task_id?: string; deleted_at?: string | null }> {
  // 如果taskId不是以task-开头，需要加上前缀
  const roadmapId = taskId.startsWith('task-') ? taskId : `task-${taskId}`;
  
  const response = await apiClient.delete(
    `/roadmaps/${roadmapId}`,
    {
      params: { user_id: userId },
    }
  );
  return response.data;
}

/**
 * 获取任务详情
 * 
 * 通过任务ID获取任务的详细信息
 */
export async function getTaskDetail(
  taskId: string
): Promise<{
  task_id: string;
  title: string;
  status: string;
  current_step: string;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  roadmap_id?: string | null;
}> {
  const response = await apiClient.get(
    `/roadmaps/${taskId}/status`
  );
  return response.data;
}

/**
 * 执行日志接口定义
 */
export interface ExecutionLogItem {
  id: string;
  task_id: string;
  roadmap_id?: string | null;
  concept_id?: string | null;
  level: 'debug' | 'info' | 'success' | 'warning' | 'error';
  category: string;
  step: string | null;
  agent_name: string | null;
  message: string;
  details: any;
  duration_ms: number | null;
  created_at: string;
}

/**
 * 执行日志列表响应
 */
export interface ExecutionLogListResponse {
  logs: ExecutionLogItem[];
  total: number;
  offset: number;
  limit: number;
}

/**
 * 获取任务执行日志
 * 
 * 获取指定任务的详细执行日志，支持按级别和分类过滤
 */
export async function getTaskLogs(
  taskId: string,
  level?: string,
  category?: string,
  limit: number = 100,
  offset: number = 0
): Promise<ExecutionLogListResponse> {
  const response = await apiClient.get<ExecutionLogListResponse>(
    `/trace/${taskId}/logs`,
    {
      params: { level, category, limit, offset },
    }
  );
  return response.data;
}

/**
 * 执行摘要接口定义
 */
export interface ExecutionSummary {
  task_id: string;
  level_stats: Record<string, number>;
  category_stats: Record<string, number>;
  total_duration_ms: number | null;
  first_log_at: string | null;
  last_log_at: string | null;
  total_logs: number;
}

/**
 * 获取任务执行摘要
 * 
 * 获取任务执行的统计摘要信息
 */
export async function getTaskSummary(
  taskId: string
): Promise<ExecutionSummary> {
  const response = await apiClient.get<ExecutionSummary>(
    `/trace/${taskId}/summary`
  );
  return response.data;
}

// ============================================================
// Intent Analysis Endpoints
// ============================================================

/**
 * 需求分析响应接口定义
 */
export interface IntentAnalysisResponse {
  id: string;
  task_id: string;
  roadmap_id?: string | null;
  parsed_goal: string;
  key_technologies: string[];
  difficulty_profile: string;
  time_constraint: string;
  recommended_focus: string[];
  user_profile_summary?: string | null;
  skill_gap_analysis: string[];
  personalized_suggestions: string[];
  estimated_learning_path_type?: string | null;
  content_format_weights?: Record<string, number> | null;
  language_preferences?: Record<string, any> | null;
  created_at?: string | null;
}

/**
 * 获取需求分析元数据
 * 
 * 从数据库的 intent_analysis_metadata 表获取需求分析的完整数据，
 * 比从日志中提取的数据更加丰富和结构化。
 * 
 * @param taskId - 任务 ID
 * @returns 需求分析元数据
 */
export async function getIntentAnalysis(
  taskId: string
): Promise<IntentAnalysisResponse> {
  const response = await apiClient.get<IntentAnalysisResponse>(
    `/intent-analysis/${taskId}`
  );
  return response.data;
}

// ============================================================
// Waitlist Endpoints
// ============================================================

export interface WaitlistJoinRequest {
  email: string;
  source?: string;
}

export interface WaitlistJoinResponse {
  success: boolean;
  message: string;
  is_new: boolean;
}

/**
 * 加入候补名单
 * 
 * 用户在首页提交邮箱后调用此接口
 */
export async function joinWaitlist(
  request: WaitlistJoinRequest
): Promise<WaitlistJoinResponse> {
  const response = await apiClient.post<WaitlistJoinResponse>(
    '/waitlist',
    request
  );
  return response.data;
}

// ============================================================
// Learning Progress Endpoints
// ============================================================

/**
 * 更新 Concept 完成状态
 * 
 * 标记或取消标记 Concept 为已完成
 */
export async function updateConceptProgress(
  roadmapId: string,
  conceptId: string,
  isCompleted: boolean
): Promise<{concept_id: string; is_completed: boolean; completed_at: string | null}> {
  const response = await apiClient.put(
    `/progress/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}`,
    { is_completed: isCompleted }
  );
  return response.data;
}

/**
 * 获取路线图进度
 * 
 * 获取用户在指定路线图中所有 Concept 的完成状态
 */
export async function getRoadmapProgress(
  roadmapId: string
): Promise<Array<{concept_id: string; is_completed: boolean; completed_at: string | null}>> {
  const response = await apiClient.get(`/progress/roadmaps/${roadmapId}/concepts`);
  return response.data;
}

/**
 * 提交 Quiz 答题记录
 * 
 * 记录用户的 Quiz 答题结果，包括得分和错题序号
 */
export async function submitQuizAttempt(
  roadmapId: string,
  conceptId: string,
  payload: {
    quiz_id: string;
    total_questions: number;
    correct_answers: number;
    score_percentage: number;
    incorrect_question_indices: number[];
  }
): Promise<any> {
  const response = await apiClient.post(
    `/progress/roadmaps/${roadmapId}/concepts/${encodeConceptId(conceptId)}/quiz`,
    payload
  );
  return response.data;
}

// ============================================================
// 技术栈能力测试 API
// ============================================================

/**
 * 获取所有可用的技术栈列表（有测验题目的）
 */
export async function getAvailableTechnologies(): Promise<{
  technologies: string[];
  count: number;
}> {
  const response = await apiClient.get('/tech-assessments/available-technologies');
  return response.data;
}

/**
 * 获取技术栈能力测验题目
 */
export async function getTechAssessment(
  technology: string,
  proficiency: string
): Promise<any> {
  const response = await apiClient.get(
    `/tech-assessments/${technology}/${proficiency}`
  );
  return response.data;
}

/**
 * 评估技术栈测验结果
 */
export async function evaluateTechAssessment(
  technology: string,
  proficiency: string,
  assessmentId: string,
  answers: string[]
): Promise<any> {
  const response = await apiClient.post(
    `/tech-assessments/${technology}/${proficiency}/evaluate`,
    { 
      assessment_id: assessmentId,
      answers 
    }
  );
  return response.data;
}

/**
 * 分析技术栈能力（LLM深度分析）
 */
export async function analyzeTechCapability(
  technology: string,
  proficiency: string,
  userId: string,
  assessmentId: string,
  answers: string[],
  saveToProfile: boolean = true
): Promise<any> {
  const response = await apiClient.post(
    `/tech-assessments/${technology}/${proficiency}/analyze`,
    {
      user_id: userId,
      assessment_id: assessmentId,
      answers,
      save_to_profile: saveToProfile,
    }
  );
  return response.data;
}

/**
 * 获取自定义技术栈测验（如果不存在会触发生成）
 */
export async function getCustomTechAssessment(
  technology: string,
  proficiency: string
): Promise<{
  status: 'generation_started' | 'ready';
  message: string;
  assessment?: any;
}> {
  const response = await apiClient.post(
    '/tech-assessments/custom',
    {
      technology,
      proficiency,
    }
  );
  return response.data;
}

// ============================================================
// Validation & Edit Records Endpoints
// ============================================================

/**
 * 获取任务的最新验证结果
 */
export async function getLatestValidation(taskId: string): Promise<any> {
  const response = await apiClient.get(`/tasks/${taskId}/validation/latest`);
  return response.data;
}

/**
 * 获取任务的所有验证历史
 */
export async function getValidationHistory(taskId: string): Promise<any[]> {
  const response = await apiClient.get(`/tasks/${taskId}/validation/history`);
  return response.data;
}

/**
 * 获取任务的最新编辑记录（包含 modified_node_ids）
 */
export async function getLatestEdit(taskId: string): Promise<any> {
  const response = await apiClient.get(`/tasks/${taskId}/edit/latest`);
  return response.data;
}

/**
 * 获取任务的所有编辑历史
 */
export async function getEditHistory(taskId: string): Promise<any[]> {
  const response = await apiClient.get(`/tasks/${taskId}/edit/history`);
  return response.data;
}

/**
 * 获取特定编辑轮次的前后对比数据
 */
export async function getEditDiff(taskId: string, editRound: number): Promise<any> {
  const response = await apiClient.get(`/tasks/${taskId}/edit/${editRound}/diff`);
  return response.data;
}

