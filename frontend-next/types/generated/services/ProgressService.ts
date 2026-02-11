/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConceptProgressUpdate } from '../models/ConceptProgressUpdate';
import type { QuizAttemptCreate } from '../models/QuizAttemptCreate';
import type { ResponseSchemaModel_ConceptProgressResponse_ } from '../models/ResponseSchemaModel_ConceptProgressResponse_';
import type { ResponseSchemaModel_List_ConceptProgressResponse__ } from '../models/ResponseSchemaModel_List_ConceptProgressResponse__';
import type { ResponseSchemaModel_QuizAttemptResponse_ } from '../models/ResponseSchemaModel_QuizAttemptResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ProgressService {
    /**
     * Update Concept Progress
     * 标记/取消 Concept 完成状态
     *
     * - **is_completed=true**: 标记完成
     * - **is_completed=false**: 取消完成
     *
     * Args:
     * roadmap_id: 路线图ID
     * concept_id: 概念ID
     * payload: 进度更新请求
     * db: 数据库会话（自动commit/rollback）
     * user_id: 用户ID
     * service: 进度服务
     *
     * Returns:
     * 更新后的进度信息
     * @returns ResponseSchemaModel_ConceptProgressResponse_ Successful Response
     * @throws ApiError
     */
    public static updateConceptProgressApiV1LearningProgressRoadmapsRoadmapIdConceptsConceptIdPut({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: ConceptProgressUpdate,
    }): CancelablePromise<ResponseSchemaModel_ConceptProgressResponse_> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/learning/progress/roadmaps/{roadmap_id}/concepts/{concept_id}',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Roadmap Progress
     * 获取某个路线图的所有Concept进度
     *
     * Args:
     * roadmap_id: 路线图ID
     * db: 数据库会话
     * user_id: 用户ID
     * service: 进度服务
     *
     * Returns:
     * 概念进度列表
     * @returns ResponseSchemaModel_List_ConceptProgressResponse__ Successful Response
     * @throws ApiError
     */
    public static getRoadmapProgressApiV1LearningProgressRoadmapsRoadmapIdConceptsGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<ResponseSchemaModel_List_ConceptProgressResponse__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/learning/progress/roadmaps/{roadmap_id}/concepts',
            path: {
                'roadmap_id': roadmapId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Submit Quiz Attempt
     * 提交Quiz答题记录
     *
     * Args:
     * roadmap_id: 路线图ID
     * concept_id: 概念ID
     * payload: 答题记录
     * db: 数据库会话（自动commit/rollback）
     * user_id: 用户ID
     * service: 进度服务
     *
     * Returns:
     * 答题记录详情
     * @returns ResponseSchemaModel_QuizAttemptResponse_ Successful Response
     * @throws ApiError
     */
    public static submitQuizAttemptApiV1LearningProgressRoadmapsRoadmapIdConceptsConceptIdQuizPost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: QuizAttemptCreate,
    }): CancelablePromise<ResponseSchemaModel_QuizAttemptResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/learning/progress/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
