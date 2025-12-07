/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LearningPreferences } from './LearningPreferences';
/**
 * 修改内容请求
 */
export type ModifyContentRequest = {
    /**
     * 用户ID
     */
    user_id: string;
    /**
     * 用户学习偏好
     */
    preferences: LearningPreferences;
    /**
     * 修改要求列表
     */
    requirements: Array<string>;
};

