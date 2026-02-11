/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 测验响应
 *
 * 概念的测验题目信息。
 */
export type QuizResponse = {
    /**
     * 路线图ID
     */
    roadmap_id: string;
    /**
     * 概念ID
     */
    concept_id: string;
    /**
     * 测验ID
     */
    quiz_id: string;
    /**
     * 题目列表
     */
    questions: Array<Record<string, any>>;
    /**
     * 总题目数
     */
    total_questions: number;
    /**
     * 简单题数量
     */
    easy_count: number;
    /**
     * 中等题数量
     */
    medium_count: number;
    /**
     * 困难题数量
     */
    hard_count: number;
    /**
     * 创建时间（ISO格式）
     */
    created_at?: (string | null);
};

