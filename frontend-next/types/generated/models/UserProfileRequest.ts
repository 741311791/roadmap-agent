/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TechStackItem } from './TechStackItem';
/**
 * 用户画像请求体
 */
export type UserProfileRequest = {
    /**
     * 所属行业
     */
    industry?: (string | null);
    /**
     * 当前职位
     */
    current_role?: (string | null);
    /**
     * 技术栈列表
     */
    tech_stack?: Array<TechStackItem>;
    /**
     * 主要语言
     */
    primary_language?: string;
    /**
     * 次要语言
     */
    secondary_language?: (string | null);
    /**
     * 每周学习时间
     */
    weekly_commitment_hours?: number;
    /**
     * 学习风格: visual, text, audio, hands_on
     */
    learning_style?: Array<string>;
    /**
     * 是否启用 AI 个性化
     */
    ai_personalization?: boolean;
};

