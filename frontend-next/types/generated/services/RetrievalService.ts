/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RetrievalService {
    /**
     * Get Roadmap
     * 获取完整的路线图数据
     *
     * Args:
     * roadmap_id: 路线图ID
     * db: 数据库会话
     * repo_factory: Repository 工厂
     * orchestrator: 工作流执行器
     *
     * Returns:
     * - 如果路线图存在，返回完整的路线图框架数据
     * - 如果路线图不存在但有活跃任务，返回生成中状态
     * - 如果都不存在，返回 404
     *
     * Raises:
     * HTTPException: 404 - 路线图不存在
     *
     * Example:
     * ```json
     * {
         * "roadmap_id": "python-web-dev-2024",
         * "title": "Python Web开发学习路线",
         * "topic": "Python Web开发",
         * "concepts": [...],
         * "status": "completed"
         * }
         * ```
         * @returns any Successful Response
         * @throws ApiError
         */
        public static getRoadmapApiV1RoadmapsRoadmapIdGet({
            roadmapId,
        }: {
            roadmapId: string,
        }): CancelablePromise<any> {
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
         * Get Active Task
         * 获取路线图当前的活跃任务
         *
         * 用于前端轮询：查询该路线图是否有正在进行的任务
         * - 如果有正在进行的任务，返回task_id和状态
         * - 如果没有，返回null
         *
         * Args:
         * roadmap_id: 路线图 ID
         * db: 数据库会话
         *
         * Returns:
         * 活跃任务信息或null
         *
         * Raises:
         * HTTPException: 404 - 路线图不存在
         *
         * Example:
         * ```json
         * {
             * "has_active_task": true,
             * "task_id": "550e8400-e29b-41d4-a716-446655440000",
             * "status": "processing",
             * "current_step": "tutorial_generation",
             * "created_at": "2024-01-01T00:00:00Z"
             * }
             * ```
             * @returns any Successful Response
             * @throws ApiError
             */
            public static getActiveTaskApiV1RoadmapsRoadmapIdActiveTaskGet({
                roadmapId,
            }: {
                roadmapId: string,
            }): CancelablePromise<any> {
                return __request(OpenAPI, {
                    method: 'GET',
                    url: '/api/v1/roadmaps/{roadmap_id}/active-task',
                    path: {
                        'roadmap_id': roadmapId,
                    },
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
        }
