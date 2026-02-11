/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WaitlistInviteItem } from './WaitlistInviteItem';
/**
 * Waitlist邀请列表响应
 */
export type WaitlistInviteListResponse = {
    items: Array<WaitlistInviteItem>;
    total: number;
    pending: number;
    invited: number;
};

