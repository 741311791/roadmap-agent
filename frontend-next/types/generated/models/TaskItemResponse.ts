/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkflowStep } from '../constants';
import type { TaskStatus } from '../constants';
/**
 * 任务列表项
 */
export type TaskItemResponse = {
    /**
     * 任务ID
     */
    task_id: string;
    /**
     * 任务状态
     */
    status: TaskStatus;
    /**
     * 当前步骤
     */
    current_step?: (string | null);
    /**
     * 路线图标题
     */
    title?: (string | null);
    /**
     * 创建时间（ISO格式）
     */
    created_at: string;
    /**
     * 更新时间（ISO格式）
     */
    updated_at: string;
    /**
     * 完成时间（ISO格式）
     */
    completed_at?: (string | null);
    /**
     * 错误信息
     */
    error_message?: (string | null);
    /**
     * 路线图ID
     */
    roadmap_id?: (string | null);
};

