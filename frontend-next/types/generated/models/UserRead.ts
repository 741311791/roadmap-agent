/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 用户读取模式
 *
 * 包含所有可对外展示的用户信息。
 */
export type UserRead = {
    id: string;
    email: string;
    is_active?: boolean;
    is_superuser?: boolean;
    is_verified?: boolean;
    username: string;
    password_expires_at?: (string | null);
    created_at?: (string | null);
};

