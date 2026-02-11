/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { GenerateSingleConceptRequest } from '../models/GenerateSingleConceptRequest';
import type { ResponseModel } from '../models/ResponseModel';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ContentSubgraphService {
    /**
     * Generate Single Concept Content
     * 独立调用单 Concept 子图生成内容（Celery 异步任务）
     *
     * 此接口允许单独重新生成某个 Concept 的内容，不依赖完整的工作流。
     * 任务将分发到 Celery Worker 执行，FastAPI 进程立即返回任务 ID。
     *
     * 架构说明：
     * - ✅ API 层只负责 HTTP 适配和 Celery 任务分发
     * - ✅ 任务在独立的 Worker 进程中执行
     * - ✅ 通过 WebSocket 推送任务进度和结果
     * - ✅ 遵循分层架构设计规范
     *
     * Args:
     * request: 请求参数
     * user: 当前用户
     *
     * Returns:
     * Celery 任务 ID 和任务状态
     *
     * Raises:
     * 500: 任务分发失败
     *
     * 使用流程：
     * 1. 调用此接口获取 celery_task_id
     * 2. 通过 WebSocket 订阅 `roadmap:{roadmap_id}` 频道
     * 3. 接收实时进度通知和最终结果
     * @returns ResponseModel Successful Response
     * @throws ApiError
     */
    public static generateSingleConceptContentApiV1SubgraphGenerateSingleConceptPost({
        requestBody,
    }: {
        requestBody: GenerateSingleConceptRequest,
    }): CancelablePromise<ResponseModel> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/subgraph/generate-single-concept',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Task Status
     * 查询 Celery 任务状态
     *
     * Args:
     * celery_task_id: Celery 任务 ID
     *
     * Returns:
     * 任务状态信息
     * @returns ResponseModel Successful Response
     * @throws ApiError
     */
    public static getTaskStatusApiV1SubgraphTaskCeleryTaskIdStatusGet({
        celeryTaskId,
    }: {
        celeryTaskId: string,
    }): CancelablePromise<ResponseModel> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/subgraph/task/{celery_task_id}/status',
            path: {
                'celery_task_id': celeryTaskId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
