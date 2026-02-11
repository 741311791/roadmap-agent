/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 评估请求模型
 */
export type EvaluateRequest = {
    /**
     * 测验ID（前端获取题目时返回的ID）
     */
    assessment_id: string;
    /**
     * 用户的答案列表（按题目顺序）
     */
    answers: Array<string>;
};

