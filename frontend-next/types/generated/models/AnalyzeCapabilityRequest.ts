/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 能力分析请求模型
 */
export type AnalyzeCapabilityRequest = {
    /**
     * 用户ID
     */
    user_id: string;
    /**
     * 测验ID
     */
    assessment_id: string;
    /**
     * 用户的答案列表（按题目顺序）
     */
    answers: Array<string>;
    /**
     * 是否保存到用户画像
     */
    save_to_profile?: boolean;
};

