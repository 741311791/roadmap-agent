/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LearningPreferences } from './LearningPreferences';
/**
 * 内容修改请求
 */
export type ModifyContentRequest = {
    /**
     * 用户 ID
     */
    user_id: string;
    /**
     * 用户学习偏好
     */
    preferences: LearningPreferences;
    /**
     * 具体修改要求列表
     */
    requirements: Array<string>;
};

