/**
 * API Endpoints - Unified Export
 * 
 * 统一导出所有业务领域API
 * 
 * 使用方式：
 * - import { authApi, usersApi, tasksApi, roadmapsApi, contentApi, adminApi } from '@/lib/api/endpoints';
 */

// ============================================================
// 导出所有业务领域API
// ============================================================

export * from './auth';
export * from './users';
export * from './tasks';
export * from './roadmaps';
export * from './content';
export * from './learning';
export * from './chat';
export * from './admin';

// ============================================================
// 命名空间导出（推荐使用）
// ============================================================

export { authApi } from './auth';
export { usersApi } from './users';
export { tasksApi } from './tasks';
export { roadmapsApi } from './roadmaps';
export { contentApi } from './content';
export { learningApi } from './learning';
export { chatApi } from './chat';
export { adminApi } from './admin';

// ============================================================
// 重新导出常用类型（从生成的类型中和本地定义）
// ============================================================

// 从生成的类型导出
export type {
  TechStackItem,
  UserProfileRequest,
  UserProfileResponse,
  RoadmapHistoryItem,
  FeaturedRoadmapItem,
  TaskStatusDetailResponse,
  IntentAnalysisResponse,
  EditRecordResponse,
  ValidationRecordResponse,
  ExecutionLogResponse,
} from '@/types/generated';

// 类型别名（向后兼容）
export type { ExecutionLogResponse as ExecutionLog } from '@/types/generated';

// 从本地API文件导出
export type { 
  TaskListItemResponse as TaskItem,
  TaskListItemResponse,
  TaskListResponse,
} from './tasks';
export type { 
  RetryContentRequest, 
  RetryContentResponse,
} from './content';
export type { RoadmapSummary, RoadmapListResponse } from './roadmaps';
export type { UserProfileData } from './users';

// ============================================================
// 重新导出常用API函数（向后兼容，包装形式）
// ============================================================

// Admin API
import { adminApi } from './admin';
export const getAvailableTechnologies = adminApi.getAvailableTechnologies;
export const joinWaitlist = adminApi.joinWaitlist;
export const requestTrialAccess = adminApi.requestTrialAccess;

// Learning API
import { learningApi } from './learning';
export const updateConceptProgress = learningApi.updateConceptProgress;
export const submitQuizAttempt = learningApi.submitQuizAttempt;
export const getRoadmapProgress = learningApi.getRoadmapProgress;
export const analyzeTechCapability = learningApi.analyzeTechCapability;
export const getTechAssessment = learningApi.getTechAssessment;
export const evaluateTechAssessment = learningApi.evaluateTechAssessment;
export const getCustomTechAssessment = learningApi.getCustomTechAssessment;

// Content API
import { contentApi } from './content';
export const getLatestTutorial = contentApi.getLatestTutorial;
export const downloadTutorialContent = contentApi.downloadTutorialContent;
export const getResourcesByConceptId = contentApi.getResourcesByConceptId;
export const getQuizByConceptId = contentApi.getQuizByConceptId;
export const regenerateTutorial = contentApi.regenerateTutorial;
export const regenerateResources = contentApi.regenerateResources;
export const regenerateQuiz = contentApi.regenerateQuiz;
export const getTutorialVersions = contentApi.getTutorialVersions;

// Tasks API
import { tasksApi } from './tasks';
export const getRoadmapActiveTask = tasksApi.getRoadmapActiveTask;
export const getRoadmapStatus = tasksApi.getById; // 别名：获取任务状态

// Roadmaps API
import { roadmapsApi } from './roadmaps';
export const getLatestEdit = roadmapsApi.getLatestEdit;
export const checkRoadmapStatusQuick = roadmapsApi.checkRoadmapStatusQuick;

// Users API
import { usersApi } from './users';
export const getUserProfile = usersApi.getUserProfile;
export const saveUserProfile = usersApi.saveUserProfile;

// Chat API
import { chatApi } from './chat';
export const chatModificationStream = chatApi.chatModificationStream;

// ============================================================
// 辅助工具函数
// ============================================================

/**
 * URL编码概念ID
 * 
 * 概念ID可能包含特殊字符（如冒号），需要在URL中进行编码
 */
export function encodeConceptId(conceptId: string): string {
  return encodeURIComponent(conceptId);
}
