/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ResourceService {
    /**
     * Get Concept Resources
     * 获取指定概念的学习资源
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * db: 数据库会话
     *
     * Returns:
     * 资源推荐列表
     *
     * Raises:
     * HTTPException: 404 - 概念没有资源推荐
     *
     * Example:
     * ```json
     * {
         * "roadmap_id": "python-web-dev-2024",
         * "concept_id": "flask-basics",
         * "resources_id": "res-001",
         * "resources": [
             * {
                 * "title": "Flask官方文档",
                 * "url": "https://flask.palletsprojects.com/",
                 * "type": "official_docs",
                 * "description": "Flask框架的官方文档"
                 * },
                 * {
                     * "title": "Flask教程视频",
                     * "url": "https://youtube.com/...",
                     * "type": "video",
                     * "description": "B站Flask入门视频教程"
                     * }
                     * ],
                     * "resources_count": 2,
                     * "search_queries_used": ["Flask教程", "Flask文档"],
                     * "generated_at": "2024-01-01T00:00:00Z"
                     * }
                     * ```
                     * @returns any Successful Response
                     * @throws ApiError
                     */
                    public static getConceptResourcesApiV1RoadmapsRoadmapIdConceptsConceptIdResourcesGet({
                        roadmapId,
                        conceptId,
                    }: {
                        roadmapId: string,
                        conceptId: string,
                    }): CancelablePromise<any> {
                        return __request(OpenAPI, {
                            method: 'GET',
                            url: '/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources',
                            path: {
                                'roadmap_id': roadmapId,
                                'concept_id': conceptId,
                            },
                            errors: {
                                422: `Validation Error`,
                            },
                        });
                    }
                }
