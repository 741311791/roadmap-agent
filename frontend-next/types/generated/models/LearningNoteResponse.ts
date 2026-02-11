/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 学习笔记响应
 */
export type LearningNoteResponse = {
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
    note_id: string;
    title?: (string | null);
    source: string;
    tags?: Array<string>;
    created_at: string;
    updated_at: string;
};

