/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class QuizService {
    /**
     * Get Concept Quiz
     * 获取指定概念的测验
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * db: 数据库会话
     *
     * Returns:
     * 测验数据，包含题目列表
     *
     * Raises:
     * HTTPException: 404 - 概念没有测验
     *
     * Example:
     * ```json
     * {
         * "roadmap_id": "python-web-dev-2024",
         * "concept_id": "flask-basics",
         * "quiz_id": "quiz-001",
         * "questions": [
             * {
                 * "question": "Flask是什么类型的框架？",
                 * "options": ["Web框架", "数据分析框架", "游戏框架", "GUI框架"],
                 * "correct_answer": 0,
                 * "explanation": "Flask是一个轻量级的Python Web框架",
                 * "difficulty": "easy"
                 * },
                 * ...
                 * ],
                 * "total_questions": 10,
                 * "easy_count": 3,
                 * "medium_count": 5,
                 * "hard_count": 2,
                 * "generated_at": "2024-01-01T00:00:00Z"
                 * }
                 * ```
                 * @returns any Successful Response
                 * @throws ApiError
                 */
                public static getConceptQuizApiV1RoadmapsRoadmapIdConceptsConceptIdQuizGet({
                    roadmapId,
                    conceptId,
                }: {
                    roadmapId: string,
                    conceptId: string,
                }): CancelablePromise<any> {
                    return __request(OpenAPI, {
                        method: 'GET',
                        url: '/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz',
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
