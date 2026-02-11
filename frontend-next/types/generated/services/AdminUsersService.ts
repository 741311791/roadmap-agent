/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { InviteUserRequest } from '../models/InviteUserRequest';
import type { ResponseSchemaModel_InviteUserResponse_ } from '../models/ResponseSchemaModel_InviteUserResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AdminUsersService {
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
}
