/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 评估结果模型
 */
export type EvaluationResult = {
    /**
     * 得分
     */
    score: number;
    /**
     * 总分
     */
    max_score: number;
    /**
     * 正确率百分比
     */
    percentage: number;
    /**
     * 答对题数
     */
    correct_count: number;
    /**
     * 题目总数
     */
    total_questions: number;
    /**
     * 建议: confirmed, adjust, downgrade
     */
    recommendation: string;
    /**
     * 建议说明
     */
    message: string;
};

