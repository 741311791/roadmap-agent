/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BatchSendInviteRequest } from '../models/BatchSendInviteRequest';
import type { ResponseSchemaModel_BatchSendInviteResponse_ } from '../models/ResponseSchemaModel_BatchSendInviteResponse_';
import type { ResponseSchemaModel_WaitlistInviteListResponse_ } from '../models/ResponseSchemaModel_WaitlistInviteListResponse_';
import type { ResponseSchemaModel_WaitlistResponse_ } from '../models/ResponseSchemaModel_WaitlistResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminWaitlistService {
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
}
