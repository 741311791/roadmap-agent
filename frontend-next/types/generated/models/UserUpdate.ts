/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 用户更新模式
 *
 * 用户自行更新信息时的输入模式。
 */
export type UserUpdate = {
    password?: (string | null);
    email?: (string | null);
    is_active?: (boolean | null);
    is_superuser?: (boolean | null);
    is_verified?: (boolean | null);
    username?: (string | null);
};

