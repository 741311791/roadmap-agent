/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LearningPreferences } from './LearningPreferences';
/**
 * 聊天修改请求
 *
 * 用于流式修改路线图的聊天式交互。
 */
export type ChatModificationRequest = {
    /**
     * 用户的自然语言修改意见
     */
    user_message: string;
    /**
     * 当前上下文（如正在查看的 concept_id）
     */
    context?: (Record<string, any> | null);
    /**
     * 用户 ID
     */
    user_id: string;
    /**
     * 用户学习偏好
     */
    preferences: LearningPreferences;
};

