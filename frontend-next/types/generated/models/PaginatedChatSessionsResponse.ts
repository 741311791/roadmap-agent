/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChatSessionResponse } from './ChatSessionResponse';
/**
 * 分页会话列表响应
 */
export type PaginatedChatSessionsResponse = {
    sessions: Array<ChatSessionResponse>;
    total: number;
    page?: number;
    page_size?: number;
};

