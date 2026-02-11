/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 验证记录响应
 *
 * 单条验证记录的完整信息。
 */
export type ValidationRecordResponse = {
    /**
     * 验证记录ID
     */
    id: string;
    /**
     * 任务ID
     */
    task_id: string;
    /**
     * 版本号
     */
    version: number;
    /**
     * 验证状态（passed/failed）
     */
    validation_status: string;
    /**
     * 发现的问题数量
     */
    issues_found: number;
    /**
     * 问题详情列表
     */
    issues_details?: null;
    /**
     * 优化建议列表
     */
    suggestions?: null;
    /**
     * 创建时间（ISO格式）
     */
    created_at: string;
};

