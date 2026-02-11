/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ResponseSchemaModel_RetryContentResponse_ } from '../models/ResponseSchemaModel_RetryContentResponse_';
import type { RetryContentRequest } from '../models/RetryContentRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ContentRegenerateService {
    /**
     * 重新生成教程
     * 重新生成单个Concept的教程内容。
     *
     * 这是Concept编辑功能的一部分，不属于Retry（checkpoint恢复）功能。
     * 直接调用TutorialGeneratorAgent重新生成，不使用LangGraph checkpoint机制。
     *
     * 适用场景：
     * - 单个教程质量不满意
     * - 需要不同风格的教程
     * - 调整教程详细度
     * @returns ResponseSchemaModel_RetryContentResponse_ Successful Response
     * @throws ApiError
     */
    public static regenerateTutorialApiV1ContentRoadmapIdConceptsConceptIdTutorialRegeneratePost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: RetryContentRequest,
    }): CancelablePromise<ResponseSchemaModel_RetryContentResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/tutorial/regenerate',
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
     * 重新生成资源推荐
     * 重新生成单个Concept的资源推荐内容。
     *
     * 这是Concept编辑功能的一部分，不属于Retry功能。
     * @returns ResponseSchemaModel_RetryContentResponse_ Successful Response
     * @throws ApiError
     */
    public static regenerateResourcesApiV1ContentRoadmapIdConceptsConceptIdResourcesRegeneratePost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: RetryContentRequest,
    }): CancelablePromise<ResponseSchemaModel_RetryContentResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/resources/regenerate',
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
     * 重新生成测验
     * 重新生成单个Concept的测验内容。
     *
     * 这是Concept编辑功能的一部分，不属于Retry功能。
     * @returns ResponseSchemaModel_RetryContentResponse_ Successful Response
     * @throws ApiError
     */
    public static regenerateQuizApiV1ContentRoadmapIdConceptsConceptIdQuizRegeneratePost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: RetryContentRequest,
    }): CancelablePromise<ResponseSchemaModel_RetryContentResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/quiz/regenerate',
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
