/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 内容重试响应
 */
export type RetryContentResponse = {
    success: boolean;
    concept_id: string;
    content_type: 'tutorial' | 'resources' | 'quiz';
    message: string;
    data?: (Record<string, any> | null);
};

