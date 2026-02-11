/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FeaturedRoadmapsResponse } from '../models/FeaturedRoadmapsResponse';
import type { ResponseSchemaModel_RoadmapHistoryResponse_ } from '../models/ResponseSchemaModel_RoadmapHistoryResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RoadmapListService {
    /**
     * Get User Roadmaps
     * 获取当前用户的路线图列表（只包括已生成完成的路线图）
     *
     * Args:
     * db: 数据库会话
     * current_user: 当前用户（从JWT提取）
     * service: 用户服务
     * limit: 返回数量限制（默认50）
     * offset: 分页偏移（默认0）
     *
     * Returns:
     * 用户的路线图列表（从 roadmap_metadata 表查询）
     *
     * Note:
     * 学习进度从 concept_progress 表获取，而不是 content_status 字段。
     * content_status 表示内容生成状态，concept_progress 表示用户学习进度。
     *
     * Example:
     * ```json
     * {
         * "code": 200,
         * "msg": "Success",
         * "data": {
             * "roadmaps": [
                 * {
                     * "roadmap_id": "python-guide-xxx",
                     * "title": "Python Web Development",
                     * "created_at": "2024-01-01T00:00:00Z",
                     * "total_concepts": 20,
                     * "completed_concepts": 5,
                     * "topic": "python web development",
                     * "status": "learning"
                     * }
                     * ],
                     * "total": 1,
                     * "in_progress_count": 0
                     * }
                     * }
                     * ```
                     * @returns ResponseSchemaModel_RoadmapHistoryResponse_ Successful Response
                     * @throws ApiError
                     */
                    public static getUserRoadmapsApiV1RoadmapsMyGet({
                        limit = 50,
                        offset,
                    }: {
                        limit?: number,
                        offset?: number,
                    }): CancelablePromise<ResponseSchemaModel_RoadmapHistoryResponse_> {
                        return __request(OpenAPI, {
                            method: 'GET',
                            url: '/api/v1/roadmaps/my',
                            query: {
                                'limit': limit,
                                'offset': offset,
                            },
                            errors: {
                                422: `Validation Error`,
                            },
                        });
                    }
                    /**
                     * Get Deleted Roadmaps
                     * 获取当前用户回收站中的路线图列表
                     *
                     * Args:
                     * db: 数据库会话
                     * current_user: 当前用户（从JWT提取）
                     * service: 用户服务
                     * limit: 返回数量限制（默认50）
                     * offset: 分页偏移（默认0）
                     *
                     * Returns:
                     * 回收站中的路线图列表，按删除时间降序排列
                     *
                     * Example:
                     * ```json
                     * {
                         * "code": 200,
                         * "msg": "Success",
                         * "data": {
                             * "roadmaps": [
                                 * {
                                     * "roadmap_id": "python-guide-xxx",
                                     * "title": "Python Web Development",
                                     * "created_at": "2024-01-01T00:00:00Z",
                                     * "total_concepts": 20,
                                     * "completed_concepts": 5,
                                     * "topic": "python web development",
                                     * "status": "deleted",
                                     * "deleted_at": "2024-01-15T00:00:00Z",
                                     * "deleted_by": "user-123"
                                     * }
                                     * ],
                                     * "total": 1,
                                     * "in_progress_count": 0
                                     * }
                                     * }
                                     * ```
                                     * @returns ResponseSchemaModel_RoadmapHistoryResponse_ Successful Response
                                     * @throws ApiError
                                     */
                                    public static getDeletedRoadmapsApiV1RoadmapsTrashGet({
                                        limit = 50,
                                        offset,
                                    }: {
                                        limit?: number,
                                        offset?: number,
                                    }): CancelablePromise<ResponseSchemaModel_RoadmapHistoryResponse_> {
                                        return __request(OpenAPI, {
                                            method: 'GET',
                                            url: '/api/v1/roadmaps/trash',
                                            query: {
                                                'limit': limit,
                                                'offset': offset,
                                            },
                                            errors: {
                                                422: `Validation Error`,
                                            },
                                        });
                                    }
                                    /**
                                     * Get Featured Roadmaps
                                     * 获取精选路线图列表
                                     *
                                     * 从配置的Featured User (admin@example.com) 获取已完成的路线图，
                                     * 用于首页Featured Roadmaps模块展示。
                                     *
                                     * Args:
                                     * limit: 返回数量限制（默认50）
                                     * offset: 分页偏移（默认0）
                                     * db: 数据库会话
                                     *
                                     * Returns:
                                     * 精选路线图列表（只包含已完成且未删除的路线图）
                                     *
                                     * Raises:
                                     * HTTPException: 404 - Featured用户不存在
                                     *
                                     * Example:
                                     * ```json
                                     * {
                                         * "roadmaps": [
                                             * {
                                                 * "roadmap_id": "roadmap-001",
                                                 * "title": "Python Web Development",
                                                 * "created_at": "2024-01-01T00:00:00",
                                                 * "total_concepts": 28,
                                                 * "completed_concepts": 0,
                                                 * "topic": "python web",
                                                 * "status": "completed"
                                                 * }
                                                 * ],
                                                 * "total": 1,
                                                 * "featured_user_id": "user-001",
                                                 * "featured_user_email": "admin@example.com"
                                                 * }
                                                 * ```
                                                 * @returns FeaturedRoadmapsResponse Successful Response
                                                 * @throws ApiError
                                                 */
                                                public static getFeaturedRoadmapsApiV1RoadmapsFeaturedGet({
                                                    limit = 50,
                                                    offset,
                                                }: {
                                                    limit?: number,
                                                    offset?: number,
                                                }): CancelablePromise<FeaturedRoadmapsResponse> {
                                                    return __request(OpenAPI, {
                                                        method: 'GET',
                                                        url: '/api/v1/roadmaps/featured',
                                                        query: {
                                                            'limit': limit,
                                                            'offset': offset,
                                                        },
                                                        errors: {
                                                            422: `Validation Error`,
                                                        },
                                                    });
                                                }
                                            }
