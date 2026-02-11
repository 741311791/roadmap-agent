/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 聊天会话响应
 */
export type ChatSessionResponse = {
    /**
     * 用户ID
     */
    user_id: string;
    /**
     * 路线图ID
     */
    roadmap_id: string;
    /**
     * 关联概念ID
     */
    concept_id?: (string | null);
    /**
     * 会话标题
     */
    title?: (string | null);
    session_id: string;
    message_count?: number;
    last_message_preview?: (string | null);
    created_at: string;
    updated_at: string;
};

