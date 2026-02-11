/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 流式聊天请求
 */
export type ChatStreamRequest = {
    /**
     * 用户ID
     */
    user_id: string;
    /**
     * 路线图ID
     */
    roadmap_id: string;
    /**
     * 概念ID
     */
    concept_id?: (string | null);
    /**
     * 用户消息
     */
    message: string;
    /**
     * 会话ID(新会话时为空)
     */
    session_id?: (string | null);
};

