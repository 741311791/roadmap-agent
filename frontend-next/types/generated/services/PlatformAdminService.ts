/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BatchAddTavilyKeysRequest } from '../models/BatchAddTavilyKeysRequest';
import type { BatchDeleteTavilyKeysRequest } from '../models/BatchDeleteTavilyKeysRequest';
import type { BatchSendInviteRequest } from '../models/BatchSendInviteRequest';
import type { BatchUpdateTavilyKeysRequest } from '../models/BatchUpdateTavilyKeysRequest';
import type { CeleryOverview } from '../models/CeleryOverview';
import type { CeleryTaskInfo } from '../models/CeleryTaskInfo';
import type { CeleryTaskListResponse } from '../models/CeleryTaskListResponse';
import type { CeleryWorkerListResponse } from '../models/CeleryWorkerListResponse';
import type { InviteUserRequest } from '../models/InviteUserRequest';
import type { ResponseSchemaModel_BatchAddTavilyKeysResponse_ } from '../models/ResponseSchemaModel_BatchAddTavilyKeysResponse_';
import type { ResponseSchemaModel_BatchDeleteTavilyKeysResponse_ } from '../models/ResponseSchemaModel_BatchDeleteTavilyKeysResponse_';
import type { ResponseSchemaModel_BatchSendInviteResponse_ } from '../models/ResponseSchemaModel_BatchSendInviteResponse_';
import type { ResponseSchemaModel_BatchUpdateTavilyKeysResponse_ } from '../models/ResponseSchemaModel_BatchUpdateTavilyKeysResponse_';
import type { ResponseSchemaModel_InviteUserResponse_ } from '../models/ResponseSchemaModel_InviteUserResponse_';
import type { ResponseSchemaModel_TavilyAPIKeyListResponse_ } from '../models/ResponseSchemaModel_TavilyAPIKeyListResponse_';
import type { ResponseSchemaModel_WaitlistInviteListResponse_ } from '../models/ResponseSchemaModel_WaitlistInviteListResponse_';
import type { ResponseSchemaModel_WaitlistResponse_ } from '../models/ResponseSchemaModel_WaitlistResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class PlatformAdminService {
    /**
     * Invite User
     * 邀请Waitlist用户
     *
     * 为指定邮箱创建用户账号，生成临时密码。
     * 只有超级管理员可以调用。
     *
     * Args:
     * request: 邀请请求（包含邮箱、密码有效期等）
     * db: 数据库会话（自动commit/rollback）
     * current_user: 当前超级管理员
     * user_manager: 用户管理器
     * email_service: 邮件服务
     *
     * Returns:
     * 邀请结果（包含用户名、密码等）
     *
     * Raises:
     * RequestError: 请求参数错误
     * InternalServerError: 服务器内部错误
     * @returns ResponseSchemaModel_InviteUserResponse_ Successful Response
     * @throws ApiError
     */
    public static inviteUserApiV1AdminUsersInvitePost({
        requestBody,
    }: {
        requestBody: InviteUserRequest,
    }): CancelablePromise<ResponseSchemaModel_InviteUserResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/admin/users/invite',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Initial Superuser
     * 创建初始超级管理员（仅在没有超级管理员时可用）
     *
     * 这是一个初始化端点，只有当系统中没有超级管理员时才能调用。
     *
     * Args:
     * email: 管理员邮箱
     * password: 管理员密码
     * db: 数据库会话（自动commit/rollback）
     * user_manager: 用户管理器
     *
     * Returns:
     * 创建结果
     *
     * Raises:
     * RequestError: 已存在超级管理员或参数错误
     * InternalServerError: 创建失败
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createInitialSuperuserApiV1AdminUsersSuperuserPost({
        email,
        password,
    }: {
        email: string,
        password: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/admin/users/superuser',
            query: {
                'email': email,
                'password': password,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Waitlist
     * 获取Waitlist用户列表（管理员）
     *
     * 只有超级管理员可以查看。
     *
     * Args:
     * db: 数据库会话
     * current_user: 当前超级管理员
     * limit: 返回数量限制
     * offset: 分页偏移
     * pending_only: 是否只返回待邀请的用户
     *
     * Returns:
     * Waitlist用户列表
     * @returns ResponseSchemaModel_WaitlistResponse_ Successful Response
     * @throws ApiError
     */
    public static getWaitlistApiV1AdminWaitlistGet({
        limit = 100,
        offset,
        pendingOnly = false,
    }: {
        limit?: number,
        offset?: number,
        pendingOnly?: boolean,
    }): CancelablePromise<ResponseSchemaModel_WaitlistResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/waitlist',
            query: {
                'limit': limit,
                'offset': offset,
                'pending_only': pendingOnly,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Waitlist Invites
     * 获取Waitlist邀请列表（包含凭证信息，管理员）
     *
     * 只有超级管理员可以查看。
     *
     * Args:
     * db: 数据库会话
     * current_user: 当前超级管理员
     * limit: 返回数量限制
     * offset: 分页偏移
     * status: 状态筛选
     *
     * Returns:
     * 邀请列表（包含用户名、密码等敏感信息）
     * @returns ResponseSchemaModel_WaitlistInviteListResponse_ Successful Response
     * @throws ApiError
     */
    public static getWaitlistInvitesApiV1AdminWaitlistInvitesGet({
        limit = 100,
        offset,
        status = 'all',
    }: {
        limit?: number,
        offset?: number,
        status?: string,
    }): CancelablePromise<ResponseSchemaModel_WaitlistInviteListResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/admin/waitlist-invites',
            query: {
                'limit': limit,
                'offset': offset,
                'status': status,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Batch Send Invites
     * 批量发送Waitlist邀请（管理员）
     *
     * 采用"一次读取，批量处理，部分提交"策略优化性能。
     * 只有超级管理员可以调用。
     *
     * Args:
     * request: 批量邀请请求
     * db: 数据库会话（自动commit/rollback）
     * current_user: 当前超级管理员
     * user_manager: 用户管理器
     * email_service: 邮件服务
     *
     * Returns:
     * 批量操作结果（成功数、失败数、错误详情）
     * @returns ResponseSchemaModel_BatchSendInviteResponse_ Successful Response
     * @throws ApiError
     */
    public static batchSendInvitesApiV1AdminWaitlistInvitesBatchSendPost({
        requestBody,
    }: {
        requestBody: BatchSendInviteRequest,
    }): CancelablePromise<ResponseSchemaModel_BatchSendInviteResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/admin/waitlist-invites/batch-send',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Create Initial Superuser
     * 创建初始超级管理员（仅在没有超级管理员时可用）
     *
     * 这是一个初始化端点，只有当系统中没有超级管理员时才能调用。
     *
     * Args:
     * email: 管理员邮箱
     * password: 管理员密码
     * db: 数据库会话（自动commit/rollback）
     * user_manager: 用户管理器
     *
     * Returns:
     * 创建结果
     *
     * Raises:
     * RequestError: 已存在超级管理员或参数错误
     * InternalServerError: 创建失败
     * @returns any Successful Response
     * @throws ApiError
     */
    public static createInitialSuperuserApiV1AdminCreateSuperuserPost({
        email,
        password,
    }: {
        email: string,
        password: string,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/admin/create-superuser',
            query: {
                'email': email,
                'password': password,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
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
}
