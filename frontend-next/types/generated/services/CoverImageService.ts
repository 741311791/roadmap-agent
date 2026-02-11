/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BatchCoverImageResponse } from '../models/BatchCoverImageResponse';
import type { BatchGenerateRequest } from '../models/BatchGenerateRequest';
import type { BatchGetCoverImagesRequest } from '../models/BatchGetCoverImagesRequest';
import type { CoverImageResponse } from '../models/CoverImageResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class CoverImageService {
    /**
     * Get Roadmap Cover Image
     * 获取路线图封面图信息（公开接口，无需认证）
     *
     * Args:
     * roadmap_id: 路线图ID
     * db: 数据库会话
     *
     * Returns:
     * 封面图信息
     * @returns CoverImageResponse Successful Response
     * @throws ApiError
     */
    public static getRoadmapCoverImageApiV1RoadmapsRoadmapIdCoverImageGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<CoverImageResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/roadmaps/{roadmap_id}/cover-image',
            path: {
                'roadmap_id': roadmapId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Generate Roadmap Cover Image
     * 触发路线图封面图生成（异步 Celery 任务）
     *
     * ✅ 架构变更：
     * - 移除 BackgroundTasks（避免 Session 泄漏）
     * - 改用 Celery 异步任务（独立进程）
     *
     * Args:
     * roadmap_id: 路线图ID
     * prompt: 可选的图片生成提示词
     * db: 数据库会话
     * current_user: 当前用户
     *
     * Returns:
     * 封面图生成状态
     * @returns CoverImageResponse Successful Response
     * @throws ApiError
     */
    public static generateRoadmapCoverImageApiV1RoadmapsRoadmapIdCoverImageGeneratePost({
        roadmapId,
        prompt,
    }: {
        roadmapId: string,
        prompt?: (string | null),
    }): CancelablePromise<CoverImageResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/roadmaps/{roadmap_id}/cover-image/generate',
            path: {
                'roadmap_id': roadmapId,
            },
            query: {
                'prompt': prompt,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Batch Generate Cover Images
     * 批量生成封面图（异步 Celery 任务）
     *
     * 仅触发 pending/failed 状态的封面图生成，跳过已成功生成的。
     *
     * ✅ 架构变更：
     * - 移除 BackgroundTasks（避免 Session 泄漏）
     * - 改用 Celery 批量任务
     *
     * Args:
     * request: 包含路线图ID列表的请求
     * db: 数据库会话
     * current_user: 当前用户
     *
     * Returns:
     * 批量生成状态，包含触发数量和跳过数量
     * @returns any Successful Response
     * @throws ApiError
     */
    public static batchGenerateCoverImagesApiV1RoadmapsCoverImagesBatchGeneratePost({
        requestBody,
    }: {
        requestBody: BatchGenerateRequest,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/roadmaps/cover-images/batch-generate',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Batch Get Cover Images
     * 批量获取路线图封面图信息（公开接口，无需认证）
     *
     * Args:
     * request: 包含路线图ID列表的请求
     * db: 数据库会话
     *
     * Returns:
     * 封面图信息列表
     * @returns BatchCoverImageResponse Successful Response
     * @throws ApiError
     */
    public static batchGetCoverImagesApiV1RoadmapsCoverImagesBatchGetPost({
        requestBody,
    }: {
        requestBody: BatchGetCoverImagesRequest,
    }): CancelablePromise<Array<BatchCoverImageResponse>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/roadmaps/cover-images/batch-get',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
