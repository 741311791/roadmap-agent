/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ResponseSchemaModel_Dict_str__Any__ } from '../models/ResponseSchemaModel_Dict_str__Any__';
import type { ResponseSchemaModel_WaitlistJoinResponse_ } from '../models/ResponseSchemaModel_WaitlistJoinResponse_';
import type { WaitlistJoinRequest } from '../models/WaitlistJoinRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class WaitlistPublicService {
    /**
     * Join Waitlist
     * 加入候补名单（公开接口，无需认证）
     *
     * 用户在首页提交邮箱后调用此接口，将邮箱存入候补名单。
     * 如果邮箱已存在，返回成功但标记为非新用户。
     *
     * Args:
     * request: 包含邮箱和来源的请求体
     * db: 数据库会话（自动commit/rollback）
     *
     * Returns:
     * 加入结果，包含成功标志和是否为新用户
     * @returns ResponseSchemaModel_WaitlistJoinResponse_ Successful Response
     * @throws ApiError
     */
    public static joinWaitlistApiV1WaitlistPost({
        requestBody,
    }: {
        requestBody: WaitlistJoinRequest,
    }): CancelablePromise<ResponseSchemaModel_WaitlistJoinResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/waitlist',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Waitlist Count
     * 获取候补名单人数（公开接口）
     *
     * Args:
     * db: 数据库会话
     *
     * Returns:
     * 候补名单统计信息
     * @returns ResponseSchemaModel_Dict_str__Any__ Successful Response
     * @throws ApiError
     */
    public static getWaitlistCountApiV1WaitlistCountGet(): CancelablePromise<ResponseSchemaModel_Dict_str__Any__> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/waitlist/count',
        });
    }
}
