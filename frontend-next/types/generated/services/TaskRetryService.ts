/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ResponseSchemaModel_RetryResponse_ } from '../models/ResponseSchemaModel_RetryResponse_';
import type { ResponseSchemaModel_TaskRetryStatus_ } from '../models/ResponseSchemaModel_TaskRetryStatus_';
import type { RetryRequest } from '../models/RetryRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TaskRetryService {
    /**
     * 获取任务重试状态
     * 查询指定任务的重试状态，包括：
     * - 是否可以重试
     * - 当前checkpoint信息
     * - 是否有子图在中断
     * - 可用的重试模式（resume/time_travel）
     *
     * 用于前端判断是否显示重试按钮以及支持的重试选项。
     * @returns ResponseSchemaModel_TaskRetryStatus_ Successful Response
     * @throws ApiError
     */
    public static getRetryStatusApiV1TasksTaskIdRetryStatusGet({
        taskId,
    }: {
        taskId: string,
    }): CancelablePromise<ResponseSchemaModel_TaskRetryStatus_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/tasks/{task_id}/retry-status',
            path: {
                'task_id': taskId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 执行任务重试
     * 执行路线图生成任务的重试操作。
     *
     * 支持两种重试模式：
     *
     * 1. **断点续传（mode=resume）**：
     * - 从最后的checkpoint自动恢复
     * - 适用于Worker重启、临时失败、主图/子图节点失败
     * - LangGraph自动处理所有并发失败的子图节点
     * - 推荐优先使用
     *
     * 2. **时间旅行（mode=time_travel）**：
     * - 回到主图历史节点重新执行
     * - 适用于用户需求变更、重新设计
     * - 仅支持主图节点（Intent、Curriculum、Validation、Content）
     * - 子图并发失败请使用断点续传
     *
     * 注意：
     * - 仅支持重试失败、部分失败或取消的任务
     * - 正在执行中的任务需要先取消
     * - 等待人工审核的任务请使用审核API
     * - 概念内容重新生成请使用 /api/v1/content/{roadmap_id}/concepts/{concept_id}/regenerate
     * @returns ResponseSchemaModel_RetryResponse_ Successful Response
     * @throws ApiError
     */
    public static retryTaskApiV1TasksTaskIdRetryPost({
        taskId,
        requestBody,
    }: {
        taskId: string,
        requestBody: RetryRequest,
    }): CancelablePromise<ResponseSchemaModel_RetryResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/tasks/{task_id}/retry',
            path: {
                'task_id': taskId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
