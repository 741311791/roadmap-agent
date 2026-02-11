/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AssessmentResponse } from './AssessmentResponse';
/**
 * 自定义测验响应模型
 */
export type CustomAssessmentResponse = {
    /**
     * generation_started | ready
     */
    status: string;
    message: string;
    assessment?: (AssessmentResponse | null);
};

