/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { QuestionResponse } from './QuestionResponse';
/**
 * 测验响应模型
 */
export type AssessmentResponse = {
    assessment_id: string;
    technology: string;
    proficiency_level: string;
    questions: Array<QuestionResponse>;
    total_questions: number;
};

