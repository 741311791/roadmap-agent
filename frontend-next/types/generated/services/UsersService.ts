/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RoadmapHistoryResponse } from '../models/RoadmapHistoryResponse';
import type { UserProfileRequest } from '../models/UserProfileRequest';
import type { UserProfileResponse } from '../models/UserProfileResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UsersService {
    /**
     * Get User Profile
     * 获取用户画像
     *
     * Args:
     * user_id: 用户 ID
     *
     * Returns:
     * 用户画像数据，如果不存在则返回默认值
     * @returns UserProfileResponse Successful Response
     * @throws ApiError
     */
    public static getUserProfileApiV1UsersUserIdProfileGet({
        userId,
    }: {
        userId: string,
    }): CancelablePromise<UserProfileResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/users/{user_id}/profile',
            path: {
                'user_id': userId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Save User Profile
     * 保存或更新用户画像
     *
     * Args:
     * user_id: 用户 ID
     * request: 用户画像数据
     *
     * Returns:
     * 保存后的用户画像
     * @returns UserProfileResponse Successful Response
     * @throws ApiError
     */
    public static saveUserProfileApiV1UsersUserIdProfilePut({
        userId,
        requestBody,
    }: {
        userId: string,
        requestBody: UserProfileRequest,
    }): CancelablePromise<UserProfileResponse> {
        return __request(OpenAPI, {
            method: 'PUT',
            url: '/api/v1/users/{user_id}/profile',
            path: {
                'user_id': userId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get User Roadmaps
     * 获取用户的所有路线图列表
     *
     * Args:
     * user_id: 用户 ID
     * limit: 返回数量限制（默认50）
     * offset: 分页偏移（默认0）
     *
     * Returns:
     * 用户的路线图列表
     * @returns RoadmapHistoryResponse Successful Response
     * @throws ApiError
     */
    public static getUserRoadmapsApiV1UsersUserIdRoadmapsGet({
        userId,
        limit = 50,
        offset,
    }: {
        userId: string,
        limit?: number,
        offset?: number,
    }): CancelablePromise<RoadmapHistoryResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/users/{user_id}/roadmaps',
            path: {
                'user_id': userId,
            },
            query: {
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
