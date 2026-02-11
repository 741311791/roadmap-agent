/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BearerResponse } from '../models/BearerResponse';
import type { Body_auth_jwt_login_api_v1_auth_jwt_login_post } from '../models/Body_auth_jwt_login_api_v1_auth_jwt_login_post';
import type { ResponseSchemaModel_BlacklistStatsResponse_ } from '../models/ResponseSchemaModel_BlacklistStatsResponse_';
import type { ResponseSchemaModel_LogoutResponse_ } from '../models/ResponseSchemaModel_LogoutResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class AuthService {
    /**
     * Logout
     * 用户登出（撤销当前 Token）
     *
     * 机制：
     * 1. 解码 Token 获取 jti（JWT ID）和过期时间
     * 2. 将 jti 加入 Redis 黑名单
     * 3. 设置过期时间 = Token 剩余有效期
     * 4. Token 过期后自动清理
     *
     * Args:
     * current_user: 当前用户（通过 JWT 验证）
     * credentials: JWT Token（从 Authorization header 获取）
     *
     * Returns:
     * 登出成功消息
     *
     * Raises:
     * RequestError: Token不包含必要字段或解码失败
     *
     * Example:
     * ```bash
     * curl -X POST http://localhost:8000/api/v1/auth/logout           -H "Authorization: Bearer eyJ..."
     * ```
     * @returns ResponseSchemaModel_LogoutResponse_ Successful Response
     * @throws ApiError
     */
    public static logoutApiV1AuthAuthLogoutPost(): CancelablePromise<ResponseSchemaModel_LogoutResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/auth/logout',
        });
    }
    /**
     * Logout All Devices
     * 强制登出所有设备（撤销用户所有 Token）
     *
     * ⚠️ 注意：此功能需要在 JWT payload 中包含 user_id 字段，
     * 并且在生成 jti 时使用特定格式（如：{user_id}:{random}）
     *
     * 当前实现：由于 jti 是随机 UUID，无法批量撤销。
     * 需要修改 JWT 策略，在 jti 中包含 user_id。
     *
     * Args:
     * current_user: 当前用户
     *
     * Returns:
     * 登出成功消息，包含清除的设备数量
     * @returns ResponseSchemaModel_LogoutResponse_ Successful Response
     * @throws ApiError
     */
    public static logoutAllDevicesApiV1AuthAuthLogoutAllDevicesPost(): CancelablePromise<ResponseSchemaModel_LogoutResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/auth/logout-all-devices',
        });
    }
    /**
     * Get Token Blacklist Stats
     * 获取 Token 黑名单统计（管理员功能）
     *
     * Args:
     * current_user: 当前用户（需要管理员权限）
     *
     * Returns:
     * 黑名单统计信息，包含总数、活跃和过期的token数量
     * @returns ResponseSchemaModel_BlacklistStatsResponse_ Successful Response
     * @throws ApiError
     */
    public static getTokenBlacklistStatsApiV1AuthAuthBlacklistStatsGet(): CancelablePromise<ResponseSchemaModel_BlacklistStatsResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/auth/auth/blacklist/stats',
        });
    }
    /**
     * Auth:Jwt.Login
     * @returns BearerResponse Successful Response
     * @throws ApiError
     */
    public static authJwtLoginApiV1AuthJwtLoginPost({
        formData,
    }: {
        formData: Body_auth_jwt_login_api_v1_auth_jwt_login_post,
    }): CancelablePromise<BearerResponse> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/jwt/login',
            formData: formData,
            mediaType: 'application/x-www-form-urlencoded',
            errors: {
                400: `Bad Request`,
                422: `Validation Error`,
            },
        });
    }
    /**
     * Auth:Jwt.Logout
     * @returns any Successful Response
     * @throws ApiError
     */
    public static authJwtLogoutApiV1AuthJwtLogoutPost(): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/auth/jwt/logout',
            errors: {
                401: `Missing token or inactive user.`,
            },
        });
    }
}
