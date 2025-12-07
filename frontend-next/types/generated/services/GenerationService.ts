/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { UserRequest } from '../models/UserRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class GenerationService {
    /**
     * Generate Roadmap Async
     * 生成学习路线图（异步任务）
     *
     * Args:
     * request: 用户请求，包含学习目标和偏好
     * background_tasks: FastAPI后台任务
     * orchestrator: 工作流执行器
     * repo_factory: Repository 工厂
     *
     * Returns:
     * 任务 ID，roadmap_id将在需求分析完成后通过WebSocket发送给前端
     *
     * Example:
     * ```json
     * {
         * "task_id": "550e8400-e29b-41d4-a716-446655440000",
         * "status": "processing",
         * "message": "路线图生成任务已启动"
         * }
         * ```
         * @returns any Successful Response
         * @throws ApiError
         */
        public static generateRoadmapAsyncApiV1RoadmapsGeneratePost({
            requestBody,
        }: {
            requestBody: UserRequest,
        }): CancelablePromise<any> {
            return __request(OpenAPI, {
                method: 'POST',
                url: '/api/v1/roadmaps/generate',
                body: requestBody,
                mediaType: 'application/json',
                errors: {
                    422: `Validation Error`,
                },
            });
        }
        /**
         * Get Generation Status
         * 查询路线图生成任务状态
         *
         * Args:
         * task_id: 任务ID
         * orchestrator: 工作流执行器
         * repo_factory: Repository 工厂
         *
         * Returns:
         * 任务状态信息
         *
         * Raises:
         * HTTPException: 404 - 任务不存在
         *
         * Example:
         * ```json
         * {
             * "task_id": "550e8400-e29b-41d4-a716-446655440000",
             * "status": "completed",
             * "current_step": "tutorial_generation",
             * "roadmap_id": "python-web-dev-2024",
             * "created_at": "2024-01-01T00:00:00Z"
             * }
             * ```
             * @returns any Successful Response
             * @throws ApiError
             */
            public static getGenerationStatusApiV1RoadmapsTaskIdStatusGet({
                taskId,
            }: {
                taskId: string,
            }): CancelablePromise<any> {
                return __request(OpenAPI, {
                    method: 'GET',
                    url: '/api/v1/roadmaps/{task_id}/status',
                    path: {
                        'task_id': taskId,
                    },
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
        }
