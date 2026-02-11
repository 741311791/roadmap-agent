/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Waitlist邀请列表项（含凭证）
 */
export type WaitlistInviteItem = {
    email: string;
    source: string;
    invited: boolean;
    invited_at?: (string | null);
    created_at: string;
    username?: (string | null);
    password?: (string | null);
    expires_at?: (string | null);
    sent_content?: (Record<string, any> | null);
};

