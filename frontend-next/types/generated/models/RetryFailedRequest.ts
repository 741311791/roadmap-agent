/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LearningPreferences } from './LearningPreferences';
/**
 * 重试失败内容请求
 */
export type RetryFailedRequest = {
    /**
     * 用户ID
     */
    user_id: string;
    /**
     * 要重试的内容类型列表
     */
    content_types?: Array<string>;
    /**
     * 用户学习偏好
     */
    preferences: LearningPreferences;
};

