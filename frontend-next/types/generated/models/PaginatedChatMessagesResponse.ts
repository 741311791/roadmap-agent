/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ChatMessageResponse } from './ChatMessageResponse';
/**
 * 分页消息列表响应
 */
export type PaginatedChatMessagesResponse = {
    messages: Array<ChatMessageResponse>;
    total: number;
    page?: number;
    page_size?: number;
};

