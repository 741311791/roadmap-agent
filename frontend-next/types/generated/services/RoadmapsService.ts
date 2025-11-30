/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChatModificationRequest } from '../models/ChatModificationRequest';
import type { ModifyContentRequest } from '../models/ModifyContentRequest';
import type { RegenerateTutorialRequest } from '../models/RegenerateTutorialRequest';
import type { RoadmapFramework } from '../models/RoadmapFramework';
import type { UserRequest } from '../models/UserRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RoadmapsService {
    /**
     * Generate Roadmap
     * 生成学习路线图（异步任务）
     *
     * Returns:
     * 任务 ID，用于后续查询状态
     * @returns any Successful Response
     * @throws ApiError
     */
    public static generateRoadmapApiV1RoadmapsGeneratePost({
        requestBody,
    }: {
        requestBody: UserRequest,
    }): CancelablePromise<Record<string, any>> {
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
     * Get Roadmap Status
     * 查询路线图生成状态
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getRoadmapStatusApiV1RoadmapsTaskIdStatusGet({
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
    /**
     * Get Roadmap
     * 获取完整的路线图数据
     * @returns RoadmapFramework Successful Response
     * @throws ApiError
     */
    public static getRoadmapApiV1RoadmapsRoadmapIdGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<RoadmapFramework> {
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
     * Approve Roadmap
     * 人工审核端点（Human-in-the-Loop）
     *
     * Args:
     * task_id: 任务 ID
     * approved: 是否批准
     * feedback: 用户反馈（如果未批准）
     * @returns any Successful Response
     * @throws ApiError
     */
    public static approveRoadmapApiV1RoadmapsTaskIdApprovePost({
        taskId,
        approved,
        feedback,
    }: {
        taskId: string,
        approved: boolean,
        feedback?: (string | null),
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/roadmaps/{task_id}/approve',
            path: {
                'task_id': taskId,
            },
            query: {
                'approved': approved,
                'feedback': feedback,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Generate Roadmap Stream
     * 流式生成学习路线图
     *
     * 使用 Server-Sent Events (SSE) 实时推送生成过程。
     *
     * Args:
     * request: 用户请求
     * include_tutorials: 是否包含教程生成阶段（默认 False）
     *
     * Returns:
     * Server-Sent Events 流
     *
     * Event 格式：
     * 需求分析和框架设计阶段：
     * - chunk: {"type": "chunk", "content": "...", "agent": "..."}
     * - complete: {"type": "complete", "data": {...}, "agent": "..."}
     *
     * 教程生成阶段（当 include_tutorials=True）：
     * - tutorials_start: {"type": "tutorials_start", "total_count": N}
     * - batch_start: {"type": "batch_start", "batch_index": 1, "batch_size": 2, ...}
     * - tutorial_start: {"type": "tutorial_start", "concept_id": "...", "concept_name": "..."}
     * - tutorial_chunk: {"type": "tutorial_chunk", "concept_id": "...", "content": "..."}
     * - tutorial_complete: {"type": "tutorial_complete", "concept_id": "...", "data": {...}}
     * - tutorial_error: {"type": "tutorial_error", "concept_id": "...", "error": "..."}
     * - batch_complete: {"type": "batch_complete", "batch_index": 1, "progress": {...}}
     * - tutorials_done: {"type": "tutorials_done", "summary": {...}}
     *
     * 完成：
     * - done: {"type": "done", "summary": {...}}
     * - error: {"type": "error", "message": "...", "agent": "..."}
     * @returns any Successful Response
     * @throws ApiError
     */
    public static generateRoadmapStreamApiV1RoadmapsGenerateStreamPost({
        requestBody,
        includeTutorials = false,
    }: {
        requestBody: UserRequest,
        includeTutorials?: boolean,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/roadmaps/generate-stream',
            query: {
                'include_tutorials': includeTutorials,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Generate Full Roadmap Stream
     * 完整流式生成学习路线图（包含教程生成）
     *
     * 这是 /generate-stream?include_tutorials=true 的便捷端点。
     * 使用 Server-Sent Events (SSE) 实时推送整个生成过程。
     *
     * 流程：需求分析 → 框架设计 → 批次教程生成
     *
     * Args:
     * request: 用户请求
     *
     * Returns:
     * Server-Sent Events 流（包含所有阶段）
     * @returns any Successful Response
     * @throws ApiError
     */
    public static generateFullRoadmapStreamApiV1RoadmapsGenerateFullStreamPost({
        requestBody,
    }: {
        requestBody: UserRequest,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/roadmaps/generate-full-stream',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Regenerate Tutorial
     * 重新生成指定概念的教程（创建新版本）
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * request: 包含用户 ID 和学习偏好
     *
     * Returns:
     * 新生成的教程元数据（包含版本号）
     *
     * 说明：
     * - 重新生成会创建新版本，不会覆盖旧版本
     * - 新版本会自动标记为最新（is_latest=True）
     * - 旧版本会被标记为非最新（is_latest=False）
     * @returns any Successful Response
     * @throws ApiError
     */
    public static regenerateTutorialApiV1RoadmapsRoadmapIdConceptsConceptIdRegeneratePost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: RegenerateTutorialRequest,
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
    /**
     * Get Tutorial Versions
     * 获取指定概念的所有教程版本历史
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     *
     * Returns:
     * 教程版本列表（按版本号降序，最新版本在前）
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
     *
     * Returns:
     * 最新版本的教程元数据
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
     *
     * Returns:
     * 指定版本的教程元数据
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
    /**
     * Regenerate Resources
     * 重新生成指定概念的学习资源
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * request: 包含用户 ID 和学习偏好
     *
     * Returns:
     * 新生成的资源推荐
     * @returns any Successful Response
     * @throws ApiError
     */
    public static regenerateResourcesApiV1RoadmapsRoadmapIdConceptsConceptIdResourcesRegeneratePost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: RegenerateTutorialRequest,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources/regenerate',
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
     * Regenerate Quiz
     * 重新生成指定概念的测验
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * request: 包含用户 ID 和学习偏好
     *
     * Returns:
     * 新生成的测验
     * @returns any Successful Response
     * @throws ApiError
     */
    public static regenerateQuizApiV1RoadmapsRoadmapIdConceptsConceptIdQuizRegeneratePost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: RegenerateTutorialRequest,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz/regenerate',
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
     * Modify Tutorial
     * 修改指定概念的教程内容
     *
     * 使用 TutorialModifierAgent 增量修改现有教程。
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
     * 使用 ResourceModifierAgent 调整现有资源推荐。
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
     * 修改指定概念的测验题目
     *
     * 使用 QuizModifierAgent 调整现有测验。
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
    /**
     * Chat Modification Stream
     * 聊天式修改入口（流式返回）
     *
     * 分析用户自然语言修改意见 → 执行修改 → 流式返回结果
     *
     * Args:
     * roadmap_id: 路线图 ID
     * request: 聊天修改请求（包含用户消息、上下文、偏好）
     *
     * Returns:
     * Server-Sent Events 流
     *
     * Event 类型：
     * - analyzing: 正在分析意图
     * - intents: 检测到的修改意图列表
     * - modifying: 正在执行某项修改
     * - result: 单个修改完成
     * - done: 全部完成 + 汇总
     * - error: 错误信息
     * @returns any Successful Response
     * @throws ApiError
     */
    public static chatModificationStreamApiV1RoadmapsRoadmapIdChatStreamPost({
        roadmapId,
        requestBody,
    }: {
        roadmapId: string,
        requestBody: ChatModificationRequest,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/roadmaps/{roadmap_id}/chat-stream',
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
}
