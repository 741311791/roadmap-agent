/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConceptStatusResponse } from '../models/ConceptStatusResponse';
import type { RoadmapConceptsStatusResponse } from '../models/RoadmapConceptsStatusResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ConceptStatusService {
    /**
     * 获取 Roadmap 的所有 Concept 状态
     * 获取某 roadmap 的所有 Concept 内容生成状态。
     *
     * **用途**：
     * - 页面刷新后恢复状态显示
     * - 查询内容生成进度
     *
     * **状态说明**：
     * - `pending`: 未开始
     * - `generating`: 生成中
     * - `completed`: 已完成
     * - `partial_failed`: 部分失败（至少一项成功）
     * - `failed`: 全部失败
     * @returns RoadmapConceptsStatusResponse Successful Response
     * @throws ApiError
     */
    public static getRoadmapConceptsStatusApiV1RoadmapsRoadmapIdGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<RoadmapConceptsStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/roadmaps/{roadmap_id}',
            path: {
                'roadmap_id': roadmapId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取单个 Concept 状态
     * 获取指定 Concept 的内容生成状态
     * @returns ConceptStatusResponse Successful Response
     * @throws ApiError
     */
    public static getConceptStatusApiV1ConceptsConceptIdGet({
        conceptId,
    }: {
        conceptId: string,
    }): CancelablePromise<ConceptStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/concepts/{concept_id}',
            path: {
                'concept_id': conceptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
