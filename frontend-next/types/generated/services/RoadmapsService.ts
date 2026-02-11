/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChatModificationRequest } from '../models/ChatModificationRequest';
import type { UserRequest } from '../models/UserRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RoadmapsService {
    /**
     * Generate Stream
     * 流式生成学习路线图（带反压机制）
     *
     * 使用 Server-Sent Events (SSE) 实时推送生成过程。
     *
     * 性能优化：
     * - 反压机制：检测客户端断开，立即停止生成，防止资源浪费
     *
     * Args:
     * http_request: FastAPI Request对象（用于检测客户端断开）
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
     * - batch_start: {"type": "batch_start", "batch_index": 1, ...}
     * - tutorial_start: {"type": "tutorial_start", "concept_id": "..."}
     * - tutorial_chunk: {"type": "tutorial_chunk", "concept_id": "..."}
     * - tutorial_complete: {"type": "tutorial_complete", "concept_id": "..."}
     * - tutorial_error: {"type": "tutorial_error", "concept_id": "..."}
     * - batch_complete: {"type": "batch_complete", "batch_index": 1, ...}
     * - tutorials_done: {"type": "tutorials_done", "summary": {...}}
     *
     * 完成：
     * - done: {"type": "done", "summary": {...}}
     * - error: {"type": "error", "message": "..."}
     * @returns any Successful Response
     * @throws ApiError
     */
    public static generateStreamApiV1RoadmapsGenerateStreamPost({
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
     * Generate Full Stream
     * 完整流式生成学习路线图（包含教程生成，带反压机制）
     *
     * 这是 /generate-stream?include_tutorials=true 的便捷端点。
     * 使用 Server-Sent Events (SSE) 实时推送整个生成过程。
     *
     * 流程：需求分析 → 框架设计 → 批次教程生成 → 保存数据库
     *
     * 性能优化：
     * - 反压机制：检测客户端断开，立即停止生成，防止LLM Token浪费
     *
     * Args:
     * http_request: FastAPI Request对象（用于检测客户端断开）
     * request: 用户请求
     *
     * Returns:
     * Server-Sent Events 流（包含所有阶段）
     * @returns any Successful Response
     * @throws ApiError
     */
    public static generateFullStreamApiV1RoadmapsGenerateFullStreamPost({
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
     * Chat Stream
     * 聊天式修改入口（流式返回，带反压机制）
     *
     * 分析用户自然语言修改意见 → 执行修改 → 流式返回结果
     *
     * 性能优化：
     * - 反压机制：检测客户端断开，立即停止生成
     *
     * Args:
     * http_request: FastAPI Request对象（用于检测客户端断开）
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
     * - agent_progress: Agent 执行进度
     * - result: 单个修改完成
     * - done: 全部完成 + 汇总
     * - error: 错误信息
     * @returns any Successful Response
     * @throws ApiError
     */
    public static chatStreamApiV1RoadmapsRoadmapIdChatStreamPost({
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
