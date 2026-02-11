/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 提交 Quiz 答题记录请求
 */
export type QuizAttemptCreate = {
    quiz_id: string;
    total_questions: number;
    correct_answers: number;
    score_percentage: number;
    /**
     * 答错题目的序号列表（从0开始，如 [0, 2, 5] 表示第1、3、6题答错）
     */
    incorrect_question_indices?: Array<number>;
};

