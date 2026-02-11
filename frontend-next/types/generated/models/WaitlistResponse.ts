/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WaitlistUserInfo } from './WaitlistUserInfo';
/**
 * Waitlist列表响应
 */
export type WaitlistResponse = {
    users: Array<WaitlistUserInfo>;
    total: number;
    pending: number;
    invited: number;
};

