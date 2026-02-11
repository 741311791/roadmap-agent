/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 题目响应模型
 */
export type QuestionResponse = {
    /**
     * 题目内容
     */
    question: string;
    /**
     * 题目类型: single_choice, multiple_choice, true_false
     */
    type: string;
    /**
     * 选项列表
     */
    options: Array<string>;
    /**
     * 题目来源级别: beginner, intermediate, expert
     */
    proficiency_level?: (string | null);
};

