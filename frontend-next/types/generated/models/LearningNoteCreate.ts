/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 创建学习笔记请求
 */
export type LearningNoteCreate = {
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
    concept_id: string;
    /**
     * 笔记内容(Markdown)
     */
    content: string;
    /**
     * 笔记标题
     */
    title?: (string | null);
    /**
     * 笔记来源
     */
    source?: 'manual' | 'ai_generated' | 'chat_extracted';
    /**
     * 标签列表
     */
    tags?: Array<string>;
};

