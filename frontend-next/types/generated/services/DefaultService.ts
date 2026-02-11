/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class DefaultService {
    /**
     * Health Check
     * 基础健康检查端点（快速响应，用于负载均衡器）
     * @returns any Successful Response
     * @throws ApiError
     */
    public static healthCheckHealthGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health',
        });
    }
    /**
     * Db Health Check
     * 数据库健康检查端点
     *
     * 检查数据库连接池状态和连接可用性。
     * 用于诊断数据库连接问题。
     * @returns any Successful Response
     * @throws ApiError
     */
    public static dbHealthCheckHealthDbGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health/db',
        });
    }
    /**
     * Detailed Health Check
     * 详细健康检查端点
     *
     * 返回所有子系统的健康状态，包括：
     * - 数据库连接池
     * - Checkpointer 连接池
     * - Redis 连接（如果有）
     * @returns any Successful Response
     * @throws ApiError
     */
    public static detailedHealthCheckHealthDetailedGet(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/health/detailed',
        });
    }
}
