/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 编辑记录响应
 *
 * 单条编辑记录的完整信息。
 */
export type EditRecordResponse = {
    /**
     * 编辑记录ID
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
     * 编辑类型（human_review/validation_failed）
     */
    edit_type: string;
    /**
     * 人工反馈内容
     */
    human_feedback?: (string | null);
    /**
     * 修改数量
     */
    modifications_count: number;
    /**
     * 创建时间（ISO格式）
     */
    created_at: string;
};

