/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChatStreamRequest } from '../models/ChatStreamRequest';
import type { LearningNoteCreate } from '../models/LearningNoteCreate';
import type { LearningNoteResponse } from '../models/LearningNoteResponse';
import type { LearningNoteUpdate } from '../models/LearningNoteUpdate';
import type { PaginatedChatMessagesResponse } from '../models/PaginatedChatMessagesResponse';
import type { PaginatedChatSessionsResponse } from '../models/PaginatedChatSessionsResponse';
import type { PaginatedLearningNotesResponse } from '../models/PaginatedLearningNotesResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class MentorService {
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
}
