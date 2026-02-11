/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AnalyzeCapabilityRequest } from '../models/AnalyzeCapabilityRequest';
import type { AnalyzeTaskResponse } from '../models/AnalyzeTaskResponse';
import type { AssessmentResponse } from '../models/AssessmentResponse';
import type { AvailableTechnologiesResponse } from '../models/AvailableTechnologiesResponse';
import type { CapabilityAnalysisResult } from '../models/CapabilityAnalysisResult';
import type { ChatStreamRequest } from '../models/ChatStreamRequest';
import type { ConceptProgressUpdate } from '../models/ConceptProgressUpdate';
import type { CustomAssessmentResponse } from '../models/CustomAssessmentResponse';
import type { CustomTechAssessmentRequest } from '../models/CustomTechAssessmentRequest';
import type { EvaluateRequest } from '../models/EvaluateRequest';
import type { EvaluationResult } from '../models/EvaluationResult';
import type { LearningNoteCreate } from '../models/LearningNoteCreate';
import type { LearningNoteResponse } from '../models/LearningNoteResponse';
import type { LearningNoteUpdate } from '../models/LearningNoteUpdate';
import type { PaginatedChatMessagesResponse } from '../models/PaginatedChatMessagesResponse';
import type { PaginatedChatSessionsResponse } from '../models/PaginatedChatSessionsResponse';
import type { PaginatedLearningNotesResponse } from '../models/PaginatedLearningNotesResponse';
import type { QuizAttemptCreate } from '../models/QuizAttemptCreate';
import type { ResponseSchemaModel_ConceptProgressResponse_ } from '../models/ResponseSchemaModel_ConceptProgressResponse_';
import type { ResponseSchemaModel_List_ConceptProgressResponse__ } from '../models/ResponseSchemaModel_List_ConceptProgressResponse__';
import type { ResponseSchemaModel_QuizAttemptResponse_ } from '../models/ResponseSchemaModel_QuizAttemptResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class LearningExperienceService {
    /**
     * Update Concept Progress
     * 标记/取消 Concept 完成状态
     *
     * - **is_completed=true**: 标记完成
     * - **is_completed=false**: 取消完成
     *
     * Args:
     * roadmap_id: 路线图ID
     * concept_id: 概念ID
     * payload: 进度更新请求
     * db: 数据库会话（自动commit/rollback）
     * user_id: 用户ID
     * service: 进度服务
     *
     * Returns:
     * 更新后的进度信息
     * @returns ResponseSchemaModel_ConceptProgressResponse_ Successful Response
     * @throws ApiError
     */
    public static updateConceptProgressApiV1LearningProgressRoadmapsRoadmapIdConceptsConceptIdPut({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: ConceptProgressUpdate,
    }): CancelablePromise<ResponseSchemaModel_ConceptProgressResponse_> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/learning/progress/roadmaps/{roadmap_id}/concepts/{concept_id}',
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
     * Get Roadmap Progress
     * 获取某个路线图的所有Concept进度
     *
     * Args:
     * roadmap_id: 路线图ID
     * db: 数据库会话
     * user_id: 用户ID
     * service: 进度服务
     *
     * Returns:
     * 概念进度列表
     * @returns ResponseSchemaModel_List_ConceptProgressResponse__ Successful Response
     * @throws ApiError
     */
    public static getRoadmapProgressApiV1LearningProgressRoadmapsRoadmapIdConceptsGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<ResponseSchemaModel_List_ConceptProgressResponse__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/learning/progress/roadmaps/{roadmap_id}/concepts',
            path: {
                'roadmap_id': roadmapId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Submit Quiz Attempt
     * 提交Quiz答题记录
     *
     * Args:
     * roadmap_id: 路线图ID
     * concept_id: 概念ID
     * payload: 答题记录
     * db: 数据库会话（自动commit/rollback）
     * user_id: 用户ID
     * service: 进度服务
     *
     * Returns:
     * 答题记录详情
     * @returns ResponseSchemaModel_QuizAttemptResponse_ Successful Response
     * @throws ApiError
     */
    public static submitQuizAttemptApiV1LearningProgressRoadmapsRoadmapIdConceptsConceptIdQuizPost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: QuizAttemptCreate,
    }): CancelablePromise<ResponseSchemaModel_QuizAttemptResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/learning/progress/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz',
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
     * Chat Stream
     * 伴学Agent流式对话（SSE）
     *
     * Args:
     * request: 聊天请求
     * service: Mentor服务
     *
     * Returns:
     * SSE流响应
     * @returns any Successful Response
     * @throws ApiError
     */
    public static chatStreamApiV1LearningMentorChatStreamPost({
        requestBody,
    }: {
        requestBody: ChatStreamRequest,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/learning/mentor/chat/stream',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Sessions
     * 获取用户的聊天会话列表
     * @returns PaginatedChatSessionsResponse Successful Response
     * @throws ApiError
     */
    public static getSessionsApiV1LearningMentorSessionsRoadmapIdGet({
        roadmapId,
        userId,
        limit = 50,
        offset,
    }: {
        roadmapId: string,
        /**
         * 用户ID
         */
        userId: string,
        /**
         * 返回数量限制
         */
        limit?: number,
        /**
         * 分页偏移
         */
        offset?: number,
    }): CancelablePromise<PaginatedChatSessionsResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/learning/mentor/sessions/{roadmap_id}',
            path: {
                'roadmap_id': roadmapId,
            },
            query: {
                'user_id': userId,
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Messages
     * 获取会话的历史消息
     * @returns PaginatedChatMessagesResponse Successful Response
     * @throws ApiError
     */
    public static getMessagesApiV1LearningMentorMessagesSessionIdGet({
        sessionId,
        limit = 50,
        offset,
    }: {
        sessionId: string,
        /**
         * 返回数量限制
         */
        limit?: number,
        /**
         * 分页偏移
         */
        offset?: number,
    }): CancelablePromise<PaginatedChatMessagesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/learning/mentor/messages/{session_id}',
            path: {
                'session_id': sessionId,
            },
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
     * Get Notes
     * 获取用户的学习笔记
     * @returns PaginatedLearningNotesResponse Successful Response
     * @throws ApiError
     */
    public static getNotesApiV1LearningMentorNotesRoadmapIdGet({
        roadmapId,
        userId,
        conceptId,
        limit = 50,
        offset,
    }: {
        roadmapId: string,
        /**
         * 用户ID
         */
        userId: string,
        /**
         * 概念ID（可选）
         */
        conceptId?: (string | null),
        /**
         * 返回数量限制
         */
        limit?: number,
        /**
         * 分页偏移
         */
        offset?: number,
    }): CancelablePromise<PaginatedLearningNotesResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/learning/mentor/notes/{roadmap_id}',
            path: {
                'roadmap_id': roadmapId,
            },
            query: {
                'user_id': userId,
                'concept_id': conceptId,
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Note
     * 创建学习笔记
     * @returns LearningNoteResponse Successful Response
     * @throws ApiError
     */
    public static createNoteApiV1LearningMentorNotesPost({
        requestBody,
    }: {
        requestBody: LearningNoteCreate,
    }): CancelablePromise<LearningNoteResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/learning/mentor/notes',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Update Note
     * 更新学习笔记
     * @returns LearningNoteResponse Successful Response
     * @throws ApiError
     */
    public static updateNoteApiV1LearningMentorNotesNoteIdPut({
        noteId,
        userId,
        requestBody,
    }: {
        noteId: string,
        /**
         * 用户ID
         */
        userId: string,
        requestBody: LearningNoteUpdate,
    }): CancelablePromise<LearningNoteResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/learning/mentor/notes/{note_id}',
            path: {
                'note_id': noteId,
            },
            query: {
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Delete Note
     * 删除学习笔记
     * @returns any Successful Response
     * @throws ApiError
     */
    public static deleteNoteApiV1LearningMentorNotesNoteIdDelete({
        noteId,
        userId,
    }: {
        noteId: string,
        /**
         * 用户ID
         */
        userId: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'DELETE',
            url: '/api/v1/learning/mentor/notes/{note_id}',
            path: {
                'note_id': noteId,
            },
            query: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Available Technologies
     * 获取所有有测验题目的技术栈列表
     *
     * Returns:
     * 所有可用技术栈的列表（去重并排序）
     *
     * Example:
     * GET /api/v1/tech-assessments/available-technologies
     * Response: {
         * "technologies": ["angular", "aws", "docker", "python", "react", ...],
         * "count": 20
         * }
         * @returns AvailableTechnologiesResponse Successful Response
         * @throws ApiError
         */
        public static getAvailableTechnologiesApiV1LearningAssessmentAvailableTechnologiesGet(): CancelablePromise<AvailableTechnologiesResponse> {
            return __request(OpenAPI, {
                method: 'GET',
                url: '/api/v1/learning/assessment/available-technologies',
            });
        }
        /**
         * Get Tech Assessment
         * 获取技术栈能力测验题目（混合级别抽选10题）
         *
         * 根据用户能力级别，从3个级别的题库中按不同比例随机抽选题目：
         * - Beginner: 7道beginner, 2道intermediate, 1道expert（侧重基础）
         * - Intermediate: 2道beginner, 6道intermediate, 2道expert（均衡分布）
         * - Expert: 1道beginner, 3道intermediate, 6道expert（侧重进阶）
         *
         * Args:
         * technology: 技术栈名称 (python, react, java等)
         * proficiency: 能力级别 (beginner, intermediate, expert)
         *
         * Returns:
         * 包含10道题目的测验数据（不包含答案和解析）
         *
         * Raises:
         * HTTPException: 404 - 测验不存在
         * HTTPException: 400 - 题库题目不足
         *
         * Example:
         * GET /api/v1/tech-assessments/python/intermediate
         * @returns AssessmentResponse Successful Response
         * @throws ApiError
         */
        public static getTechAssessmentApiV1LearningAssessmentTechnologyProficiencyGet({
            technology,
            proficiency,
        }: {
            technology: string,
            proficiency: string,
        }): CancelablePromise<AssessmentResponse> {
            return __request(OpenAPI, {
                method: 'GET',
                url: '/api/v1/learning/assessment/{technology}/{proficiency}',
                path: {
                    'technology': technology,
                    'proficiency': proficiency,
                },
                errors: {
                    422: `Validation Error`,
                },
            });
        }
        /**
         * Evaluate Assessment
         * 评估测验结果（支持混合级别题目）
         *
         * 从缓存中获取用户的测验题目（包含答案），进行评估。
         *
         * 计算加权分数：
         * - Beginner题: 1分
         * - Intermediate题: 2分
         * - Expert题: 3分
         *
         * 判定逻辑：
         * - ≥80%: confirmed - 确认当前级别
         * - 60-79%: adjust - 建议保持当前级别
         * - <60%: downgrade - 建议降低级别
         *
         * Args:
         * technology: 技术栈名称
         * proficiency: 能力级别
         * request: 包含测验ID和用户答案的请求
         *
         * Returns:
         * 评估结果，包括得分、正确率和建议
         *
         * Raises:
         * HTTPException: 404 - 测验会话不存在或已过期
         * HTTPException: 400 - 答案数量与题目数量不匹配
         *
         * Example:
         * POST /api/v1/tech-assessments/python/intermediate/evaluate
         * {
             * "assessment_id": "uuid",
             * "answers": ["选项A", "选项B", ...]
             * }
             * @returns EvaluationResult Successful Response
             * @throws ApiError
             */
            public static evaluateAssessmentApiV1LearningAssessmentTechnologyProficiencyEvaluatePost({
                technology,
                proficiency,
                requestBody,
            }: {
                technology: string,
                proficiency: string,
                requestBody: EvaluateRequest,
            }): CancelablePromise<EvaluationResult> {
                return __request(OpenAPI, {
                    method: 'POST',
                    url: '/api/v1/learning/assessment/{technology}/{proficiency}/evaluate',
                    path: {
                        'technology': technology,
                        'proficiency': proficiency,
                    },
                    body: requestBody,
                    mediaType: 'application/json',
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
            /**
             * Analyze Capability
             * 分析用户的技术栈能力（异步任务）
             *
             * 触发异步分析任务，立即返回任务ID。
             * 用户可以通过查询接口获取分析结果。
             *
             * 基于LLM深度分析用户的答题情况，重点关注错题，提供：
             * - 整体能力评价
             * - 优势和薄弱点分析
             * - 知识缺口识别
             * - 个性化学习建议
             * - 能力级别验证
             *
             * Args:
             * technology: 技术栈名称
             * proficiency: 能力级别
             * request: 包含测验ID、用户ID、答案列表和是否保存到画像的标志
             *
             * Returns:
             * 任务触发状态和任务ID
             *
             * Raises:
             * HTTPException: 404 - 测验会话不存在或已过期
             * HTTPException: 400 - 答案数量不匹配
             *
             * Example:
             * POST /api/v1/learning/assessment/python/intermediate/analyze
             * {
                 * "user_id": "user123",
                 * "assessment_id": "uuid",
                 * "answers": ["选项A", "选项B", ...],
                 * "save_to_profile": true
                 * }
                 *
                 * Response:
                 * {
                     * "status": "processing",
                     * "task_id": "task-uuid",
                     * "message": "分析任务已启动，请稍后查看结果"
                     * }
                     * @returns AnalyzeTaskResponse Successful Response
                     * @throws ApiError
                     */
                    public static analyzeCapabilityApiV1LearningAssessmentTechnologyProficiencyAnalyzePost({
                        technology,
                        proficiency,
                        requestBody,
                    }: {
                        technology: string,
                        proficiency: string,
                        requestBody: AnalyzeCapabilityRequest,
                    }): CancelablePromise<AnalyzeTaskResponse> {
                        return __request(OpenAPI, {
                            method: 'POST',
                            url: '/api/v1/learning/assessment/{technology}/{proficiency}/analyze',
                            path: {
                                'technology': technology,
                                'proficiency': proficiency,
                            },
                            body: requestBody,
                            mediaType: 'application/json',
                            errors: {
                                422: `Validation Error`,
                            },
                        });
                    }
                    /**
                     * Get Analyze Result
                     * 查询技术能力分析结果
                     *
                     * 从Redis缓存中获取最近的分析结果（24小时内有效）
                     *
                     * Args:
                     * technology: 技术栈名称
                     * proficiency: 能力级别
                     * user_id: 用户ID（查询参数）
                     *
                     * Returns:
                     * - CapabilityAnalysisResult: 分析完成时返回完整结果
                     * - None: 任务还在处理中时返回None（前端应定期轮询）
                     *
                     * Raises:
                     * HTTPException: 404 - 分析结果不存在或已过期
                     *
                     * Example:
                     * GET /api/v1/learning/assessment/python/intermediate/analyze-result?user_id=user123
                     * @returns any Successful Response
                     * @throws ApiError
                     */
                    public static getAnalyzeResultApiV1LearningAssessmentTechnologyProficiencyAnalyzeResultGet({
                        technology,
                        proficiency,
                        userId,
                    }: {
                        technology: string,
                        proficiency: string,
                        userId: string,
                    }): CancelablePromise<(CapabilityAnalysisResult | null)> {
                        return __request(OpenAPI, {
                            method: 'GET',
                            url: '/api/v1/learning/assessment/{technology}/{proficiency}/analyze-result',
                            path: {
                                'technology': technology,
                                'proficiency': proficiency,
                            },
                            query: {
                                'user_id': userId,
                            },
                            errors: {
                                422: `Validation Error`,
                            },
                        });
                    }
                    /**
                     * Get Custom Tech Assessment
                     * 获取自定义技术栈测验
                     *
                     * - 检查数据库是否已存在该技术栈的所有级别题库
                     * - 如果不存在，后台生成题库（3个级别）
                     * - 如果已存在，直接返回题目
                     *
                     * Args:
                     * request: 包含技术栈名称和能力级别
                     * background_tasks: FastAPI 后台任务
                     * db: 数据库会话
                     *
                     * Returns:
                     * 生成状态或测验题目
                     *
                     * Example:
                     * POST /api/v1/tech-assessments/custom
                     * {
                         * "technology": "hive",
                         * "proficiency": "intermediate"
                         * }
                         * @returns CustomAssessmentResponse Successful Response
                         * @throws ApiError
                         */
                        public static getCustomTechAssessmentApiV1LearningAssessmentCustomPost({
                            requestBody,
                        }: {
                            requestBody: CustomTechAssessmentRequest,
                        }): CancelablePromise<CustomAssessmentResponse> {
                            return __request(OpenAPI, {
                                method: 'POST',
                                url: '/api/v1/learning/assessment/custom',
                                body: requestBody,
                                mediaType: 'application/json',
                                errors: {
                                    422: `Validation Error`,
                                },
                            });
                        }
                        /**
                         * 查询测验题初始化进度
                         * 查询技术栈测验题的初始化进度（用于空白数据库初始化后的进度监控）
                         * @returns any Successful Response
                         * @throws ApiError
                         */
                        public static getAssessmentInitializationProgressApiV1LearningAssessmentInitializationProgressGet(): CancelablePromise<any> {
                            return __request(OpenAPI, {
                                method: 'GET',
                                url: '/api/v1/learning/assessment/initialization-progress',
                            });
                        }
                        /**
                         * 手动触发测验题初始化
                         * 手动触发技术栈测验题的异步生成任务（用于补全缺失的题目）
                         * @returns any Successful Response
                         * @throws ApiError
                         */
                        public static triggerAssessmentInitializationApiV1LearningAssessmentTriggerInitializationPost(): CancelablePromise<any> {
                            return __request(OpenAPI, {
                                method: 'POST',
                                url: '/api/v1/learning/assessment/trigger-initialization',
                            });
                        }
                    }
