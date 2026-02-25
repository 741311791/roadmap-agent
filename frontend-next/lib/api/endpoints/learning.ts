/**
 * 学习体验 API
 * 
 * 对应后端: backend/app/api/v1/endpoints/learning/
 */

import { apiClient } from '../client';
import type {
  AssessmentResponse,
  CustomAssessmentResponse,
  EvaluationResult,
  ConceptProgressResponse,
  ConceptProgressUpdate,
} from '@/types/generated';

/**
 * 学习体验 API
 */
export const learningApi = {
  /**
   * 获取技术评估问题
   * 
   * 路径: GET /learning/assessment/{technology}/{proficiency}
   */
  getTechAssessment: async (technology: string, proficiency: string = 'intermediate'): Promise<AssessmentResponse> => {
    const { data } = await apiClient.get<AssessmentResponse>(
      `/learning/assessment/${technology}/${proficiency}`
    );
    return data;
  },

  /**
   * 评估技术能力
   * 
   * 路径: POST /learning/assessment/{technology}/{proficiency}/evaluate
   */
  evaluateTechAssessment: async (
    technology: string,
    proficiency: string,
    assessmentId: string,
    answers: string[]
  ): Promise<EvaluationResult> => {
    const { data } = await apiClient.post<EvaluationResult>(
      `/learning/assessment/${technology}/${proficiency}/evaluate`,
      { assessment_id: assessmentId, answers }
    );
    return data;
  },

  /**
   * 获取自定义技术评估
   * 
   * 路径: GET /learning/assessment/custom
   */
  getCustomTechAssessment: async (): Promise<CustomAssessmentResponse> => {
    const { data } = await apiClient.get<CustomAssessmentResponse>(
      '/learning/assessment/custom'
    );
    return data;
  },

  /**
   * 分析技术能力（异步触发）
   * 
   * 路径: POST /learning/assessment/{technology}/{proficiency}/analyze
   * 
   * 返回任务ID，用户需要稍后查询结果
   */
  analyzeTechCapability: async (
    technology: string,
    proficiency: string,
    analysisData: {
      user_id: string;
      assessment_id: string;
      answers: string[];
      save_to_profile: boolean;
    }
  ): Promise<{
    status: string;
    task_id: string;
    message: string;
    technology: string;
    proficiency: string;
  }> => {
    const { data } = await apiClient.post(
      `/learning/assessment/${technology}/${proficiency}/analyze`,
      analysisData
    );
    return data;
  },

  /**
   * 查询技术能力分析结果
   * 
   * 路径: GET /learning/assessment/{technology}/{proficiency}/analyze-result
   */
  getAnalyzeResult: async (
    technology: string,
    proficiency: string,
    userId: string
  ): Promise<any> => {
    const { data } = await apiClient.get(
      `/learning/assessment/${technology}/${proficiency}/analyze-result`,
      { params: { user_id: userId } }
    );
    return data;
  },

  /**
   * 获取路线图学习进度
   * 
   * 路径: GET /learning/progress/roadmaps/{roadmapId}/concepts
   */
  getRoadmapProgress: async (roadmapId: string): Promise<any> => {
    const { data } = await apiClient.get(
      `/learning/progress/roadmaps/${roadmapId}/concepts`
    );
    return data;
  },

  /**
   * 更新概念学习进度
   * 
   * 路径: PUT /learning/progress/roadmaps/{roadmapId}/concepts/{conceptId}
   */
  updateConceptProgress: async (
    roadmapId: string,
    conceptId: string,
    progressData: ConceptProgressUpdate
  ): Promise<ConceptProgressResponse> => {
    const { data } = await apiClient.put<ConceptProgressResponse>(
      `/learning/progress/roadmaps/${roadmapId}/concepts/${conceptId}`,
      progressData
    );
    return data;
  },

  /**
   * 提交测验答案
   * 
   * 路径: POST /learning/progress/roadmaps/{roadmapId}/concepts/{conceptId}/quiz
   */
  submitQuizAttempt: async (
    roadmapId: string,
    conceptId: string,
    attemptData: {
      quiz_id: string;
      total_questions: number;
      correct_answers: number;
      score_percentage: number;
      incorrect_question_indices?: number[];
    }
  ): Promise<any> => {
    const { data } = await apiClient.post(
      `/learning/progress/roadmaps/${roadmapId}/concepts/${conceptId}/quiz`,
      attemptData
    );
    return data;
  },
};

