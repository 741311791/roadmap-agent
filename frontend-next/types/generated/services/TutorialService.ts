/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TutorialService {
    /**
     * Get Tutorial Versions
     * 获取指定概念的所有教程版本历史
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * db: 数据库会话
     *
     * Returns:
     * 教程版本列表（按版本号降序，最新版本在前）
     *
     * Raises:
     * HTTPException: 404 - 概念没有教程
     *
     * Example:
     * ```json
     * {
         * "roadmap_id": "python-web-dev-2024",
         * "concept_id": "flask-basics",
         * "total_versions": 3,
         * "tutorials": [
             * {
                 * "tutorial_id": "tut-001",
                 * "title": "Flask基础入门",
                 * "content_version": 3,
                 * "is_latest": true,
                 * "content_status": "completed"
                 * },
                 * ...
                 * ]
                 * }
                 * ```
                 * @returns any Successful Response
                 * @throws ApiError
                 */
                public static getTutorialVersionsApiV1RoadmapsRoadmapIdConceptsConceptIdTutorialsGet({
                    roadmapId,
                    conceptId,
                }: {
                    roadmapId: string,
                    conceptId: string,
                }): CancelablePromise<any> {
                    return __request(OpenAPI, {
                        method: 'GET',
                        url: '/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials',
                        path: {
                            'roadmap_id': roadmapId,
                            'concept_id': conceptId,
                        },
                        errors: {
                            422: `Validation Error`,
                        },
                    });
                }
                /**
                 * Get Latest Tutorial
                 * 获取指定概念的最新教程版本
                 *
                 * Args:
                 * roadmap_id: 路线图 ID
                 * concept_id: 概念 ID
                 * db: 数据库会话
                 *
                 * Returns:
                 * 最新版本的教程元数据
                 *
                 * Raises:
                 * HTTPException: 404 - 概念没有教程
                 *
                 * Example:
                 * ```json
                 * {
                     * "roadmap_id": "python-web-dev-2024",
                     * "concept_id": "flask-basics",
                     * "tutorial_id": "tut-001",
                     * "title": "Flask基础入门",
                     * "summary": "学习Flask框架的基础知识",
                     * "content_url": "s3://...",
                     * "content_version": 3,
                     * "is_latest": true,
                     * "content_status": "completed",
                     * "estimated_completion_time": 2.5,
                     * "generated_at": "2024-01-01T00:00:00Z"
                     * }
                     * ```
                     * @returns any Successful Response
                     * @throws ApiError
                     */
                    public static getLatestTutorialApiV1RoadmapsRoadmapIdConceptsConceptIdTutorialsLatestGet({
                        roadmapId,
                        conceptId,
                    }: {
                        roadmapId: string,
                        conceptId: string,
                    }): CancelablePromise<any> {
                        return __request(OpenAPI, {
                            method: 'GET',
                            url: '/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest',
                            path: {
                                'roadmap_id': roadmapId,
                                'concept_id': conceptId,
                            },
                            errors: {
                                422: `Validation Error`,
                            },
                        });
                    }
                    /**
                     * Get Tutorial By Version
                     * 获取指定概念的特定版本教程
                     *
                     * Args:
                     * roadmap_id: 路线图 ID
                     * concept_id: 概念 ID
                     * version: 版本号
                     * db: 数据库会话
                     *
                     * Returns:
                     * 指定版本的教程元数据
                     *
                     * Raises:
                     * HTTPException: 404 - 指定版本的教程不存在
                     *
                     * Example:
                     * ```json
                     * {
                         * "roadmap_id": "python-web-dev-2024",
                         * "concept_id": "flask-basics",
                         * "tutorial_id": "tut-001",
                         * "title": "Flask基础入门",
                         * "content_version": 2,
                         * "is_latest": false,
                         * "content_status": "completed",
                         * "generated_at": "2023-12-01T00:00:00Z"
                         * }
                         * ```
                         * @returns any Successful Response
                         * @throws ApiError
                         */
                        public static getTutorialByVersionApiV1RoadmapsRoadmapIdConceptsConceptIdTutorialsVVersionGet({
                            roadmapId,
                            conceptId,
                            version,
                        }: {
                            roadmapId: string,
                            conceptId: string,
                            version: number,
                        }): CancelablePromise<any> {
                            return __request(OpenAPI, {
                                method: 'GET',
                                url: '/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/v{version}',
                                path: {
                                    'roadmap_id': roadmapId,
                                    'concept_id': conceptId,
                                    'version': version,
                                },
                                errors: {
                                    422: `Validation Error`,
                                },
                            });
                        }
                    }
