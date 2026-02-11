/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 加入候补名单响应
 *
 * Args:
 * success: 是否成功
 * message: 提示消息
 * is_new: 是否为新用户（首次加入）
 * position: 在候补名单中的位置（可选）
 */
export type WaitlistJoinResponse = {
    success: boolean;
    message: string;
    is_new: boolean;
    position?: (number | null);
};

