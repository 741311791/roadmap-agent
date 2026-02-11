/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ModifyContentRequest } from '../models/ModifyContentRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ModificationService {
    /**
     * Modify Quiz
     * 修改指定概念的测验内容
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * request: 修改请求
     * session: 数据库会话
     * service: 内容服务
     *
     * Returns:
     * 修改后的测验信息
     *
     * Raises:
     * HTTPException: 404/500 错误
     * @returns any Successful Response
     * @throws ApiError
     */
    public static modifyQuizApiV1RoadmapIdConceptsConceptIdQuizModifyPost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: ModifyContentRequest,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/{roadmap_id}/concepts/{concept_id}/quiz/modify',
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
