/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TaskStatus } from '../constants';
import type { AssessmentResponse } from './AssessmentResponse';
/**
 * 自定义测验响应模型
 */
export type CustomAssessmentResponse = {
    /**
     * generation_started | ready
     */
    status: TaskStatus;
    message: string;
    assessment?: (AssessmentResponse | null);
};

