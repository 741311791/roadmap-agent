/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 聊天消息响应
 */
export type ChatMessageResponse = {
    /**
     * 消息角色
     */
    role: 'user' | 'assistant' | 'system';
    /**
     * 消息内容
     */
    content: string;
    message_id: string;
    session_id: string;
    intent_type?: (string | null);
    created_at: string;
};

