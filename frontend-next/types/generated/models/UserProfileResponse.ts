/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 用户画像响应体
 */
export type UserProfileResponse = {
    user_id: string;
    industry?: (string | null);
    current_role?: (string | null);
    tech_stack?: Array<Record<string, any>>;
    primary_language?: string;
    secondary_language?: (string | null);
    weekly_commitment_hours?: number;
    learning_style?: Array<string>;
    ai_personalization?: boolean;
    created_at?: (string | null);
    updated_at?: (string | null);
};

