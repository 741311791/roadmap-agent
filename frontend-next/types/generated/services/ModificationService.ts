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
     * Modify Tutorial
     * 修改指定概念的教程内容
     *
     * 使用 TutorialModifierAgent 增量修改现有教程
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * request: 修改请求，包含修改要求
     * db: 数据库会话
     *
     * Returns:
     * 修改后的教程信息
     *
     * Raises:
     * HTTPException:
     * - 404: 路线图、概念或教程不存在
     * - 500: 修改失败
     *
     * Example:
     * ```json
     * {
         * "success": true,
         * "concept_id": "flask-basics",
         * "tutorial_id": "tut-001",
         * "title": "Flask基础入门（修订版）",
         * "content_version": 4,
         * "modification_summary": "增加了代码示例，简化了技术术语",
         * "changes_made": ["添加3个实战代码示例", "重写专业术语说明"]
         * }
         * ```
         * @returns any Successful Response
         * @throws ApiError
         */
        public static modifyTutorialApiV1RoadmapsRoadmapIdConceptsConceptIdTutorialModifyPost({
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
                url: '/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/modify',
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
         * Modify Resources
         * 修改指定概念的学习资源
         *
         * 使用 ResourceModifierAgent 调整现有资源推荐
         *
         * Args:
         * roadmap_id: 路线图 ID
         * concept_id: 概念 ID
         * request: 修改请求，包含修改要求
         * db: 数据库会话
         *
         * Returns:
         * 修改后的资源信息
         *
         * Raises:
         * HTTPException:
         * - 404: 路线图、概念或资源不存在
         * - 500: 修改失败
         *
         * Example:
         * ```json
         * {
             * "success": true,
             * "concept_id": "flask-basics",
             * "resources_id": "res-001-v2",
             * "resources_count": 5,
             * "modification_summary": "添加了视频教程资源，移除了过时链接",
             * "changes_made": ["新增2个视频教程", "替换1个官方文档链接"]
             * }
             * ```
             * @returns any Successful Response
             * @throws ApiError
             */
            public static modifyResourcesApiV1RoadmapsRoadmapIdConceptsConceptIdResourcesModifyPost({
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
                    url: '/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources/modify',
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
             * Modify Quiz
             * 修改指定概念的测验内容
             *
             * 使用 QuizModifierAgent 调整现有测验题目
             *
             * Args:
             * roadmap_id: 路线图 ID
             * concept_id: 概念 ID
             * request: 修改请求，包含修改要求
             * db: 数据库会话
             *
             * Returns:
             * 修改后的测验信息
             *
             * Raises:
             * HTTPException:
             * - 404: 路线图、概念或测验不存在
             * - 500: 修改失败
             *
             * Example:
             * ```json
             * {
                 * "success": true,
                 * "concept_id": "flask-basics",
                 * "quiz_id": "quiz-001-v2",
                 * "total_questions": 12,
                 * "modification_summary": "增加了难题，调整了题目顺序",
                 * "changes_made": ["新增3道hard难度题", "重新排序题目"]
                 * }
                 * ```
                 * @returns any Successful Response
                 * @throws ApiError
                 */
                public static modifyQuizApiV1RoadmapsRoadmapIdConceptsConceptIdQuizModifyPost({
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
                        url: '/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz/modify',
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
