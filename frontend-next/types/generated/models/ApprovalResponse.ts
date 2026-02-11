/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 审核响应模型
 */
export type ApprovalResponse = {
    /**
     * 审核状态：approved/rejected
     */
    status: string;
    /**
     * 状态消息
     */
    message: string;
    /**
     * 任务ID
     */
    task_id: string;
    /**
     * 反馈意见
     */
    feedback?: (string | null);
};

