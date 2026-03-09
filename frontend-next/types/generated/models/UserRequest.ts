/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LearningPreferences } from './LearningPreferences';
/**
 * 系统输入：用户请求
 */
export type UserRequest = {
    user_id: string;
    session_id: string;
    preferences: LearningPreferences;
    /**
     * 额外补充信息
     */
    additional_context?: (string | null);
    /**
     * 极速模式：跳过结构验证节点，Curriculum Design 后直接进入 Human Review
     */
    turbo_mode?: boolean;
};

