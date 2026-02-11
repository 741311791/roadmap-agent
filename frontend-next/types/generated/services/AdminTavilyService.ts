/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BatchAddTavilyKeysRequest } from '../models/BatchAddTavilyKeysRequest';
import type { BatchDeleteTavilyKeysRequest } from '../models/BatchDeleteTavilyKeysRequest';
import type { BatchUpdateTavilyKeysRequest } from '../models/BatchUpdateTavilyKeysRequest';
import type { ResponseSchemaModel_BatchAddTavilyKeysResponse_ } from '../models/ResponseSchemaModel_BatchAddTavilyKeysResponse_';
import type { ResponseSchemaModel_BatchDeleteTavilyKeysResponse_ } from '../models/ResponseSchemaModel_BatchDeleteTavilyKeysResponse_';
import type { ResponseSchemaModel_BatchUpdateTavilyKeysResponse_ } from '../models/ResponseSchemaModel_BatchUpdateTavilyKeysResponse_';
import type { ResponseSchemaModel_TavilyAPIKeyListResponse_ } from '../models/ResponseSchemaModel_TavilyAPIKeyListResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminTavilyService {
    /**
     * Get Tavily Keys
     * 获取所有Tavily API Keys
     *
     * 只有超级管理员可以查看。
     *
     * Args:
     * db: 数据库会话
     * current_user: 当前超级管理员
     *
     * Returns:
     * API Key列表（脱敏显示）
     * @returns ResponseSchemaModel_TavilyAPIKeyListResponse_ Successful Response
     * @throws ApiError
     */
    public static getTavilyKeysApiV1AdminTavilyKeysGet(): CancelablePromise<ResponseSchemaModel_TavilyAPIKeyListResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/tavily/keys',
        });
    }
    /**
     * Batch Add Tavily Keys
     * 批量添加Tavily API Keys
     *
     * 采用"一次读取，批量处理，一次提交"策略优化性能。
     * 只有超级管理员可以调用。
     *
     * Args:
     * request: 批量API Key请求
     * db: 数据库会话（自动commit/rollback）
     * current_user: 当前超级管理员
     *
     * Returns:
     * 批量操作结果
     * @returns ResponseSchemaModel_BatchAddTavilyKeysResponse_ Successful Response
     * @throws ApiError
     */
    public static batchAddTavilyKeysApiV1AdminTavilyKeysBatchPost({
        requestBody,
    }: {
        requestBody: BatchAddTavilyKeysRequest,
    }): CancelablePromise<ResponseSchemaModel_BatchAddTavilyKeysResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/admin/tavily/keys/batch',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Batch Update Tavily Keys
     * 批量更新Tavily API Keys配额（通过官方API查询）
     *
     * 工作流程：
     * 1. 从数据库读取指定的API Keys
     * 2. 对每个Key调用Tavily官方API查询当前配额
     * 3. 更新数据库中的remaining_quota和plan_limit
     *
     * 只有超级管理员可以调用。
     *
     * Args:
     * request: 批量更新请求（包含待更新的API Keys列表）
     * db: 数据库会话（自动commit/rollback）
     * current_user: 当前超级管理员
     *
     * Returns:
     * 批量更新结果
     * @returns ResponseSchemaModel_BatchUpdateTavilyKeysResponse_ Successful Response
     * @throws ApiError
     */
    public static batchUpdateTavilyKeysApiV1AdminTavilyKeysBatchUpdatePost({
        requestBody,
    }: {
        requestBody: BatchUpdateTavilyKeysRequest,
    }): CancelablePromise<ResponseSchemaModel_BatchUpdateTavilyKeysResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/admin/tavily/keys/batch-update',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Batch Delete Tavily Keys
     * 批量删除Tavily API Keys
     *
     * 采用"一次读取，批量删除，一次提交"策略优化性能。
     * 只有超级管理员可以调用。
     *
     * Args:
     * request: 批量删除请求（包含待删除的API Keys列表）
     * db: 数据库会话（自动commit/rollback）
     * current_user: 当前超级管理员
     *
     * Returns:
     * 批量删除结果
     * @returns ResponseSchemaModel_BatchDeleteTavilyKeysResponse_ Successful Response
     * @throws ApiError
     */
    public static batchDeleteTavilyKeysApiV1AdminTavilyKeysBatchDeletePost({
        requestBody,
    }: {
        requestBody: BatchDeleteTavilyKeysRequest,
    }): CancelablePromise<ResponseSchemaModel_BatchDeleteTavilyKeysResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/admin/tavily/keys/batch-delete',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Refresh All Tavily Keys Quota
     * 刷新所有Tavily API Keys的配额信息
     *
     * 自动获取数据库中所有的API Keys，并通过Tavily官方API查询最新配额。
     * 只有超级管理员可以调用。
     *
     * Args:
     * db: 数据库会话（自动commit/rollback）
     * current_user: 当前超级管理员
     *
     * Returns:
     * 批量更新结果
     * @returns ResponseSchemaModel_BatchUpdateTavilyKeysResponse_ Successful Response
     * @throws ApiError
     */
    public static refreshAllTavilyKeysQuotaApiV1AdminTavilyKeysRefreshQuotaPost(): CancelablePromise<ResponseSchemaModel_BatchUpdateTavilyKeysResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/admin/tavily/keys/refresh-quota',
        });
    }
}
