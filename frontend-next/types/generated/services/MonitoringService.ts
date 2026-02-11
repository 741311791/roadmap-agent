/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CeleryOverview } from '../models/CeleryOverview';
import type { CeleryTaskInfo } from '../models/CeleryTaskInfo';
import type { CeleryTaskListResponse } from '../models/CeleryTaskListResponse';
import type { CeleryWorkerListResponse } from '../models/CeleryWorkerListResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class MonitoringService {
    /**
     * Get Celery Overview
     * 获取 Celery 任务队列总览
     *
     * 返回当前队列中的任务统计信息，包括活跃、待处理任务数和队列长度。
     * 只有超级管理员可以访问。
     *
     * Returns:
     * Celery 任务队列总览数据
     * @returns CeleryOverview Successful Response
     * @throws ApiError
     */
    public static getCeleryOverviewApiV1AdminCeleryOverviewGet(): CancelablePromise<CeleryOverview> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/celery/overview',
        });
    }
    /**
     * Get Celery Tasks
     * 获取 Celery 任务列表
     *
     * 支持按状态和队列筛选，返回当前队列中的任务列表。
     * 只有超级管理员可以访问。
     *
     * Args:
     * status: 筛选状态 (active, scheduled, reserved, all)
     * queue: 筛选队列 (default, all)
     * limit: 返回数量限制
     * offset: 偏移量
     *
     * Returns:
     * Celery 任务列表
     * @returns CeleryTaskListResponse Successful Response
     * @throws ApiError
     */
    public static getCeleryTasksApiV1AdminCeleryTasksGet({
        status,
        queue,
        limit = 50,
        offset,
    }: {
        /**
         * 筛选状态: active, scheduled, reserved, all
         */
        status?: (string | null),
        /**
         * 筛选队列: default, all
         */
        queue?: (string | null),
        /**
         * 返回数量限制
         */
        limit?: number,
        /**
         * 偏移量
         */
        offset?: number,
    }): CancelablePromise<CeleryTaskListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/celery/tasks',
            query: {
                'status': status,
                'queue': queue,
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Celery Task Detail
     * 获取单个 Celery 任务详情
     *
     * 通过任务 ID 查询任务的详细信息，包括状态、结果、错误等。
     * 只有超级管理员可以访问。
     *
     * Args:
     * task_id: 任务 ID
     *
     * Returns:
     * Celery 任务详细信息
     * @returns CeleryTaskInfo Successful Response
     * @throws ApiError
     */
    public static getCeleryTaskDetailApiV1AdminCeleryTasksTaskIdGet({
        taskId,
    }: {
        taskId: string,
    }): CancelablePromise<CeleryTaskInfo> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/celery/tasks/{task_id}',
            path: {
                'task_id': taskId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Celery Workers
     * 获取 Celery Worker 列表
     *
     * 返回当前活跃的 Worker 信息，包括主机名、状态、活跃任务数等。
     * 只有超级管理员可以访问。
     *
     * Returns:
     * Celery Worker 列表
     * @returns CeleryWorkerListResponse Successful Response
     * @throws ApiError
     */
    public static getCeleryWorkersApiV1AdminCeleryWorkersGet(): CancelablePromise<CeleryWorkerListResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/celery/workers',
        });
    }
    /**
     * Get Api Rate Limits
     * 获取所有API的速率限制使用情况
     *
     * 返回各API Provider的当前速率使用情况，包括：
     * - current_count: 当前1分钟窗口内的请求数
     * - limit: 配置的速率限制（RPM）
     * - usage_percent: 使用率百分比
     * - available: 剩余可用次数
     *
     * 只有超级管理员可以访问。
     *
     * Returns:
     * 所有Provider的速率使用情况
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getApiRateLimitsApiV1AdminCeleryApiRateLimitsGet(): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/celery/api-rate-limits',
        });
    }
    /**
     * Get Api Rate Limit By Provider
     * 获取指定API Provider的速率限制使用情况
     *
     * Args:
     * provider: API Provider名称（如openai, anthropic, deepseek, tavily）
     *
     * Returns:
     * 该Provider的速率使用情况
     * @returns any Successful Response
     * @throws ApiError
     */
    public static getApiRateLimitByProviderApiV1AdminCeleryApiRateLimitsProviderGet({
        provider,
    }: {
        provider: string,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/celery/api-rate-limits/{provider}',
            path: {
                'provider': provider,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Reset Api Rate Limit
     * 重置指定API Provider的速率限制（清空窗口记录）
     *
     * 用于紧急情况下清空某个Provider的请求记录，重置速率限制。
     *
     * Args:
     * provider: API Provider名称（如openai, anthropic, deepseek, tavily）
     *
     * Returns:
     * 操作结果
     * @returns any Successful Response
     * @throws ApiError
     */
    public static resetApiRateLimitApiV1AdminCeleryApiRateLimitsProviderResetPost({
        provider,
    }: {
        provider: string,
    }): CancelablePromise<Record<string, any>> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/admin/celery/api-rate-limits/{provider}/reset',
            path: {
                'provider': provider,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
