/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Quiz 答题记录响应
 */
export type QuizAttemptResponse = {
    id: string;
    quiz_id: string;
    concept_id: string;
    total_questions: number;
    correct_answers: number;
    score_percentage: number;
    incorrect_question_indices: Array<number>;
    attempted_at: string;
};

