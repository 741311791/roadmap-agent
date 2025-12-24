/**
 * 内容相关 API 端点
 */

import { apiClient } from '../client';

/**
 * 教程响应
 */
export interface TutorialResponse {
  concept_id: string;
  concept_title: string;
  version: number;
  content_url: string;
  content_preview?: string;
  created_at: string;
  status: string;
}

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
 * 内容 API
 */
export const contentApi = {
  /**
   * 获取教程内容
   */
  getTutorial: async (
    roadmapId: string,
    conceptId: string,
    version?: number
  ): Promise<TutorialResponse> => {
    const { data } = await apiClient.get<TutorialResponse>(
      `/roadmaps/${roadmapId}/concepts/${conceptId}/tutorial`,
      { params: version ? { version } : undefined }
    );
    return data;
  },

  /**
   * 获取学习资源
   */
  getResources: async (
    roadmapId: string,
    conceptId: string
  ): Promise<ResourcesResponse> => {
    const { data } = await apiClient.get<ResourcesResponse>(
      `/roadmaps/${roadmapId}/concepts/${conceptId}/resources`
    );
    return data;
  },

  /**
   * 获取测验题目
   */
  getQuiz: async (
    roadmapId: string,
    conceptId: string
  ): Promise<QuizResponse> => {
    const { data } = await apiClient.get<QuizResponse>(
      `/roadmaps/${roadmapId}/concepts/${conceptId}/quiz`
    );
    return data;
  },

  /**
   * 修改教程内容
   */
  modifyTutorial: async (
    roadmapId: string,
    conceptId: string,
    request: ModifyContentRequest
  ): Promise<ModifyContentResponse> => {
    const { data } = await apiClient.post<ModifyContentResponse>(
      `/roadmaps/${roadmapId}/concepts/${conceptId}/tutorial/modify`,
      request
    );
    return data;
  },

  /**
   * 修改学习资源
   */
  modifyResources: async (
    roadmapId: string,
    conceptId: string,
    request: ModifyContentRequest
  ): Promise<ModifyContentResponse> => {
    const { data } = await apiClient.post<ModifyContentResponse>(
      `/roadmaps/${roadmapId}/concepts/${conceptId}/resources/modify`,
      request
    );
    return data;
  },

  /**
   * 修改测验题目
   */
  modifyQuiz: async (
    roadmapId: string,
    conceptId: string,
    request: ModifyContentRequest
  ): Promise<ModifyContentResponse> => {
    const { data } = await apiClient.post<ModifyContentResponse>(
      `/roadmaps/${roadmapId}/concepts/${conceptId}/quiz/modify`,
      request
    );
    return data;
  },
};
