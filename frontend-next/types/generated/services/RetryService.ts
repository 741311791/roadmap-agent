/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RegenerateContentRequest } from '../models/RegenerateContentRequest';
import type { RetryFailedRequest } from '../models/RetryFailedRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RetryService {
    /**
     * Retry Failed Content
     * 断点续传：重新生成失败的内容
     *
     * 精确到内容类型粒度，只重跑失败的部分：
     * - content_status='failed' 的教程
     * - resources_status='failed' 的资源推荐
     * - quiz_status='failed' 的测验
     *
     * Args:
     * roadmap_id: 路线图 ID
     * request: 包含用户偏好和要重试的内容类型
     * background_tasks: FastAPI后台任务
     * db: 数据库会话
     *
     * Returns:
     * task_id 用于 WebSocket 订阅进度
     *
     * Example:
     * ```json
     * {
         * "task_id": "550e8400-e29b-41d4-a716-446655440000",
         * "roadmap_id": "python-web-dev-2024",
         * "status": "processing",
         * "items_to_retry": {
             * "tutorial": 3,
             * "resources": 2,
             * "quiz": 1
             * },
             * "total_items": 6,
             * "message": "开始重试 6 个失败项目"
             * }
             * ```
             * @returns any Successful Response
             * @throws ApiError
             */
            public static retryFailedContentApiV1RoadmapsRoadmapIdRetryFailedPost({
                roadmapId,
                requestBody,
            }: {
                roadmapId: string,
                requestBody: RetryFailedRequest,
            }): CancelablePromise<any> {
                return __request(OpenAPI, {
                    method: 'POST',
                    url: '/api/v1/roadmaps/{roadmap_id}/retry-failed',
                    path: {
                        'roadmap_id': roadmapId,
                    },
                    body: requestBody,
                    mediaType: 'application/json',
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
            /**
             * Regenerate Concept Content
             * 重新生成指定概念的所有内容（教程+资源+测验）
             *
             * 用于用户不满意当前内容，想要完全重新生成的场景
             *
             * Args:
             * roadmap_id: 路线图 ID
             * concept_id: 概念 ID
             * request: 包含用户 ID 和学习偏好
             * db: 数据库会话
             *
             * Returns:
             * 重新生成的结果
             *
             * Raises:
             * HTTPException: 404 - 路线图或概念不存在
             *
             * Example:
             * ```json
             * {
                 * "success": true,
                 * "concept_id": "flask-basics",
                 * "regenerated": {
                     * "tutorial": true,
                     * "resources": true,
                     * "quiz": true
                     * },
                     * "message": "内容重新生成成功"
                     * }
                     * ```
                     * @returns any Successful Response
                     * @throws ApiError
                     */
                    public static regenerateConceptContentApiV1RoadmapsRoadmapIdConceptsConceptIdRegeneratePost({
                        roadmapId,
                        conceptId,
                        requestBody,
                    }: {
                        roadmapId: string,
                        conceptId: string,
                        requestBody: RegenerateContentRequest,
                    }): CancelablePromise<any> {
                        return __request(OpenAPI, {
                            method: 'POST',
                            url: '/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/regenerate',
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
