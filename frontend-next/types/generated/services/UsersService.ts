/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ResponseSchemaModel_UserProfileResponse_ } from '../models/ResponseSchemaModel_UserProfileResponse_';
import type { UserProfileRequest } from '../models/UserProfileRequest';
import type { UserRead } from '../models/UserRead';
import type { UserUpdate } from '../models/UserUpdate';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class UsersService {
    /**
     * Get User Profile
     * 获取用户画像（从JWT自动提取user_id）
     *
     * Args:
     * db: 数据库会话
     * current_user: 当前用户（从JWT提取）
     * service: 用户服务
     *
     * Returns:
     * 用户画像数据，如果不存在则返回默认值
     *
     * Example:
     * ```json
     * {
         * "code": 200,
         * "msg": "Success",
         * "data": {
             * "user_id": "user-123",
             * "industry": "Technology",
             * "current_role": "Software Engineer",
             * "tech_stack": [
                 * {
                     * "technology": "Python",
                     * "proficiency": "intermediate",
                     * "capability_analysis": {}
                     * }
                     * ],
                     * "primary_language": "zh",
                     * "weekly_commitment_hours": 10,
                     * "learning_style": ["text", "hands_on"],
                     * "ai_personalization": true
                     * }
                     * }
                     * ```
                     * @returns ResponseSchemaModel_UserProfileResponse_ Successful Response
                     * @throws ApiError
                     */
                    public static getUserProfileApiV1UsersProfileGet(): CancelablePromise<ResponseSchemaModel_UserProfileResponse_> {
                        return __request(OpenAPI, {
                            method: 'GET',
                            url: '/api/v1/users/profile',
                        });
                    }
                    /**
                     * Get User Profile
                     * 获取用户画像（从JWT自动提取user_id）
                     *
                     * Args:
                     * db: 数据库会话
                     * current_user: 当前用户（从JWT提取）
                     * service: 用户服务
                     *
                     * Returns:
                     * 用户画像数据，如果不存在则返回默认值
                     *
                     * Example:
                     * ```json
                     * {
                         * "code": 200,
                         * "msg": "Success",
                         * "data": {
                             * "user_id": "user-123",
                             * "industry": "Technology",
                             * "current_role": "Software Engineer",
                             * "tech_stack": [
                                 * {
                                     * "technology": "Python",
                                     * "proficiency": "intermediate",
                                     * "capability_analysis": {}
                                     * }
                                     * ],
                                     * "primary_language": "zh",
                                     * "weekly_commitment_hours": 10,
                                     * "learning_style": ["text", "hands_on"],
                                     * "ai_personalization": true
                                     * }
                                     * }
                                     * ```
                                     * @returns ResponseSchemaModel_UserProfileResponse_ Successful Response
                                     * @throws ApiError
                                     */
                                    public static getUserProfileApiV1UsersProfileGet1(): CancelablePromise<ResponseSchemaModel_UserProfileResponse_> {
                                        return __request(OpenAPI, {
                                            method: 'GET',
                                            url: '/api/v1/users/profile',
                                        });
                                    }
                                    /**
                                     * Save User Profile
                                     * 保存或更新用户画像（从JWT自动提取user_id）
                                     *
                                     * Args:
                                     * request: 用户画像数据
                                     * db: 数据库会话（自动commit/rollback）
                                     * current_user: 当前用户（从JWT提取）
                                     * service: 用户服务
                                     *
                                     * Returns:
                                     * 保存后的用户画像
                                     *
                                     * Example Request:
                                     * ```json
                                     * {
                                         * "industry": "Technology",
                                         * "current_role": "Software Engineer",
                                         * "tech_stack": [
                                             * {
                                                 * "technology": "Python",
                                                 * "proficiency": "intermediate"
                                                 * }
                                                 * ],
                                                 * "primary_language": "zh",
                                                 * "weekly_commitment_hours": 15,
                                                 * "learning_style": ["text", "hands_on"],
                                                 * "ai_personalization": true
                                                 * }
                                                 * ```
                                                 * @returns ResponseSchemaModel_UserProfileResponse_ Successful Response
                                                 * @throws ApiError
                                                 */
                                                public static saveUserProfileApiV1UsersProfilePut({
                                                    requestBody,
                                                }: {
                                                    requestBody: UserProfileRequest,
                                                }): CancelablePromise<ResponseSchemaModel_UserProfileResponse_> {
                                                    return __request(OpenAPI, {
                                                        method: 'PUT',
                                                        url: '/api/v1/users/profile',
                                                        body: requestBody,
                                                        mediaType: 'application/json',
                                                        errors: {
                                                            422: `Validation Error`,
                                                        },
                                                    });
                                                }
                                                /**
                                                 * Save User Profile
                                                 * 保存或更新用户画像（从JWT自动提取user_id）
                                                 *
                                                 * Args:
                                                 * request: 用户画像数据
                                                 * db: 数据库会话（自动commit/rollback）
                                                 * current_user: 当前用户（从JWT提取）
                                                 * service: 用户服务
                                                 *
                                                 * Returns:
                                                 * 保存后的用户画像
                                                 *
                                                 * Example Request:
                                                 * ```json
                                                 * {
                                                     * "industry": "Technology",
                                                     * "current_role": "Software Engineer",
                                                     * "tech_stack": [
                                                         * {
                                                             * "technology": "Python",
                                                             * "proficiency": "intermediate"
                                                             * }
                                                             * ],
                                                             * "primary_language": "zh",
                                                             * "weekly_commitment_hours": 15,
                                                             * "learning_style": ["text", "hands_on"],
                                                             * "ai_personalization": true
                                                             * }
                                                             * ```
                                                             * @returns ResponseSchemaModel_UserProfileResponse_ Successful Response
                                                             * @throws ApiError
                                                             */
                                                            public static saveUserProfileApiV1UsersProfilePut1({
                                                                requestBody,
                                                            }: {
                                                                requestBody: UserProfileRequest,
                                                            }): CancelablePromise<ResponseSchemaModel_UserProfileResponse_> {
                                                                return __request(OpenAPI, {
                                                                    method: 'PUT',
                                                                    url: '/api/v1/users/profile',
                                                                    body: requestBody,
                                                                    mediaType: 'application/json',
                                                                    errors: {
                                                                        422: `Validation Error`,
                                                                    },
                                                                });
                                                            }
                                                            /**
                                                             * Users:Current User
                                                             * @returns UserRead Successful Response
                                                             * @throws ApiError
                                                             */
                                                            public static usersCurrentUserApiV1UsersMeGet(): CancelablePromise<UserRead> {
                                                                return __request(OpenAPI, {
                                                                    method: 'GET',
                                                                    url: '/api/v1/users/me',
                                                                    errors: {
                                                                        401: `Missing token or inactive user.`,
                                                                    },
                                                                });
                                                            }
                                                            /**
                                                             * Users:Patch Current User
                                                             * @returns UserRead Successful Response
                                                             * @throws ApiError
                                                             */
                                                            public static usersPatchCurrentUserApiV1UsersMePatch({
                                                                requestBody,
                                                            }: {
                                                                requestBody: UserUpdate,
                                                            }): CancelablePromise<UserRead> {
                                                                return __request(OpenAPI, {
                                                                    method: 'PATCH',
                                                                    url: '/api/v1/users/me',
                                                                    body: requestBody,
                                                                    mediaType: 'application/json',
                                                                    errors: {
                                                                        400: `Bad Request`,
                                                                        401: `Missing token or inactive user.`,
                                                                        422: `Validation Error`,
                                                                    },
                                                                });
                                                            }
                                                            /**
                                                             * Users:User
                                                             * @returns UserRead Successful Response
                                                             * @throws ApiError
                                                             */
                                                            public static usersUserApiV1UsersIdGet({
                                                                id,
                                                            }: {
                                                                id: string,
                                                            }): CancelablePromise<UserRead> {
                                                                return __request(OpenAPI, {
                                                                    method: 'GET',
                                                                    url: '/api/v1/users/{id}',
                                                                    path: {
                                                                        'id': id,
                                                                    },
                                                                    errors: {
                                                                        401: `Missing token or inactive user.`,
                                                                        403: `Not a superuser.`,
                                                                        404: `The user does not exist.`,
                                                                        422: `Validation Error`,
                                                                    },
                                                                });
                                                            }
                                                            /**
                                                             * Users:Patch User
                                                             * @returns UserRead Successful Response
                                                             * @throws ApiError
                                                             */
                                                            public static usersPatchUserApiV1UsersIdPatch({
                                                                id,
                                                                requestBody,
                                                            }: {
                                                                id: string,
                                                                requestBody: UserUpdate,
                                                            }): CancelablePromise<UserRead> {
                                                                return __request(OpenAPI, {
                                                                    method: 'PATCH',
                                                                    url: '/api/v1/users/{id}',
                                                                    path: {
                                                                        'id': id,
                                                                    },
                                                                    body: requestBody,
                                                                    mediaType: 'application/json',
                                                                    errors: {
                                                                        400: `Bad Request`,
                                                                        401: `Missing token or inactive user.`,
                                                                        403: `Not a superuser.`,
                                                                        404: `The user does not exist.`,
                                                                        422: `Validation Error`,
                                                                    },
                                                                });
                                                            }
                                                            /**
                                                             * Users:Delete User
                                                             * @returns void
                                                             * @throws ApiError
                                                             */
                                                            public static usersDeleteUserApiV1UsersIdDelete({
                                                                id,
                                                            }: {
                                                                id: string,
                                                            }): CancelablePromise<void> {
                                                                return __request(OpenAPI, {
                                                                    method: 'DELETE',
                                                                    url: '/api/v1/users/{id}',
                                                                    path: {
                                                                        'id': id,
                                                                    },
                                                                    errors: {
                                                                        401: `Missing token or inactive user.`,
                                                                        403: `Not a superuser.`,
                                                                        404: `The user does not exist.`,
                                                                        422: `Validation Error`,
                                                                    },
                                                                });
                                                            }
                                                        }
