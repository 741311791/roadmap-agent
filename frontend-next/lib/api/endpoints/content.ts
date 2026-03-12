/**
 * 内容相关 API 端点
 */

import { apiClient } from '../client';

/**
 * 教程响应（使用后端的 TutorialDetailResponse）
 */
import type { TutorialDetailResponse } from '@/types/generated';
export type TutorialResponse = TutorialDetailResponse;

/**
 * 资源响应
 */
export interface ResourcesResponse {
  concept_id: string;
  concept_title: string;
  resources: Resource[];
  status: string;
}

export interface Resource {
  title: string;
  url: string;
  type: 'article' | 'video' | 'documentation' | 'tutorial' | 'course';
  description: string;
  difficulty_level: 'beginner' | 'intermediate' | 'advanced';
  estimated_time?: string;
}

/**
 * 测验响应
 */
export interface QuizResponse {
  concept_id: string;
  concept_title: string;
  questions: Question[];
  status: string;
}

export interface Question {
  question_id: string;
  type: 'multiple_choice' | 'single_choice' | 'true_false' | 'short_answer';
  question_text: string;
  options?: string[];
  correct_answer: string | string[];
  explanation: string;
  difficulty: 'easy' | 'medium' | 'hard';
}

/**
 * 修改请求
 */
export interface ModifyContentRequest {
  modification_request: string;
  current_version?: number;
}

/**
 * 修改响应
 */
export interface ModifyContentResponse {
  concept_id: string;
  new_version?: number;
  content_url?: string;
  status: string;
  message: string;
}

/**
 * 重新生成内容请求
 */
export type RetryContentRequest = {
  user_feedback?: string;
  force?: boolean;
};

/**
 * 重新生成内容响应
 */
export type RetryContentResponse = {
  success: boolean;
  concept_id: string;
  content_type: string;
  message: string;
  new_content?: any;
  data?: Record<string, any> | null;
};

/**
 * 内容 API
 */
export const contentApi = {
  /**
   * 获取教程内容（特定版本）
   */
  getTutorial: async (
    roadmapId: string,
    conceptId: string,
    version?: number
  ): Promise<TutorialResponse> => {
    const endpoint = version
      ? `/content/${roadmapId}/concepts/${conceptId}/tutorials/v${version}`
      : `/content/${roadmapId}/concepts/${conceptId}/tutorials/latest`;
    
    // ✅ apiClient 已经通过 extractDataInterceptor 自动提取了 data 字段
    // 不需要再次访问 data.data
    const { data } = await apiClient.get<TutorialResponse>(endpoint);
    return data;
  },

  /**
   * 获取最新教程（别名函数）
   */
  getLatestTutorial: async (
    roadmapId: string,
    conceptId: string
  ): Promise<TutorialResponse> => {
    return contentApi.getTutorial(roadmapId, conceptId);
  },

  /**
   * 获取教程版本列表
   * 
   * 旧路径: GET /content/tutorials/{roadmap_id}/{concept_id}/versions
   * 新路径: GET /content/{roadmap_id}/concepts/{concept_id}/tutorials
   */
  getTutorialVersions: async (
    roadmapId: string,
    conceptId: string
  ): Promise<any> => {
    const { data } = await apiClient.get(
      `/content/${roadmapId}/concepts/${conceptId}/tutorials`
    );
    return data;
  },

  /**
   * 下载教程内容
   * 
   * 路径: GET /content/{roadmapId}/concepts/{conceptId}/tutorials/latest/content
   */
  downloadTutorialContent: async (
    roadmapId: string,
    conceptId: string
  ): Promise<Blob> => {
    const { data } = await apiClient.get(
      `/content/${roadmapId}/concepts/${conceptId}/tutorials/latest/content`,
      { responseType: 'blob' }
    );
    return data;
  },

  /**
   * 获取学习资源
   * 
   * 旧路径: GET /roadmaps/{roadmap_id}/concepts/{concept_id}/resources
   * 新路径: GET /content/{roadmap_id}/concepts/{concept_id}/resources
   */
  getResources: async (
    roadmapId: string,
    conceptId: string
  ): Promise<ResourcesResponse> => {
    const { data } = await apiClient.get<ResourcesResponse>(
      `/content/${roadmapId}/concepts/${conceptId}/resources`
    );
    return data;
  },

  /**
   * 获取学习资源（别名函数）
   */
  getResourcesByConceptId: async (
    roadmapId: string,
    conceptId: string
  ): Promise<ResourcesResponse> => {
    return contentApi.getResources(roadmapId, conceptId);
  },

  /**
   * 获取测验题目
   * 
   * 旧路径: GET /roadmaps/{roadmap_id}/concepts/{concept_id}/quiz
   * 新路径: GET /content/{roadmap_id}/concepts/{concept_id}/quiz
   */
  getQuiz: async (
    roadmapId: string,
    conceptId: string
  ): Promise<QuizResponse> => {
    const { data } = await apiClient.get<QuizResponse>(
      `/content/${roadmapId}/concepts/${conceptId}/quiz`
    );
    return data;
  },

  /**
   * 获取测验题目（别名函数）
   */
  getQuizByConceptId: async (
    roadmapId: string,
    conceptId: string
  ): Promise<QuizResponse> => {
    return contentApi.getQuiz(roadmapId, conceptId);
  },

  /**
   * 修改教程内容
   * 
   * 旧路径: POST /roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/modify
   * 新路径: POST /content/{roadmap_id}/concepts/{concept_id}/tutorial/modify
   */
  modifyTutorial: async (
    roadmapId: string,
    conceptId: string,
    request: ModifyContentRequest
  ): Promise<ModifyContentResponse> => {
    const { data } = await apiClient.post<ModifyContentResponse>(
      `/content/${roadmapId}/concepts/${conceptId}/tutorial/modify`,
      request
    );
    return data;
  },

  /**
   * 修改学习资源
   * 
   * 旧路径: POST /roadmaps/{roadmap_id}/concepts/{concept_id}/resources/modify
   * 新路径: POST /content/{roadmap_id}/concepts/{concept_id}/resources/modify
   */
  modifyResources: async (
    roadmapId: string,
    conceptId: string,
    request: ModifyContentRequest
  ): Promise<ModifyContentResponse> => {
    const { data } = await apiClient.post<ModifyContentResponse>(
      `/content/${roadmapId}/concepts/${conceptId}/resources/modify`,
      request
    );
    return data;
  },

  /**
   * 修改测验题目
   * 
   * 旧路径: POST /roadmaps/{roadmap_id}/concepts/{concept_id}/quiz/modify
   * 新路径: POST /content/{roadmap_id}/concepts/{concept_id}/quiz/modify
   */
  modifyQuiz: async (
    roadmapId: string,
    conceptId: string,
    request: ModifyContentRequest
  ): Promise<ModifyContentResponse> => {
    const { data } = await apiClient.post<ModifyContentResponse>(
      `/content/${roadmapId}/concepts/${conceptId}/quiz/modify`,
      request
    );
    return data;
  },

  /**
   * 重新生成教程
   * 
   * 路径: POST /content/{roadmap_id}/concepts/{concept_id}/tutorial/regenerate
   * 说明: 调用TutorialGeneratorAgent重新生成指定概念的教程内容
   */
  regenerateTutorial: async (
    roadmapId: string,
    conceptId: string,
    request?: RetryContentRequest
  ): Promise<RetryContentResponse> => {
    const { data } = await apiClient.post<RetryContentResponse>(
      `/content/${roadmapId}/concepts/${conceptId}/tutorial/regenerate`,
      request || {}
    );
    return data;
  },

  /**
   * 重新生成资源推荐
   * 
   * 路径: POST /content/{roadmap_id}/concepts/{concept_id}/resources/regenerate
   * 说明: 调用ResourceRecommenderAgent重新生成指定概念的资源推荐
   */
  regenerateResources: async (
    roadmapId: string,
    conceptId: string,
    request?: RetryContentRequest
  ): Promise<RetryContentResponse> => {
    const { data } = await apiClient.post<RetryContentResponse>(
      `/content/${roadmapId}/concepts/${conceptId}/resources/regenerate`,
      request || {}
    );
    return data;
  },

  /**
   * 重新生成测验
   * 
   * 路径: POST /content/{roadmap_id}/concepts/{concept_id}/quiz/regenerate
   * 说明: 调用QuizGeneratorAgent重新生成指定概念的测验内容
   */
  regenerateQuiz: async (
    roadmapId: string,
    conceptId: string,
    request?: RetryContentRequest
  ): Promise<RetryContentResponse> => {
    const { data } = await apiClient.post<RetryContentResponse>(
      `/content/${roadmapId}/concepts/${conceptId}/quiz/regenerate`,
      request || {}
    );
    return data;
  },
};
