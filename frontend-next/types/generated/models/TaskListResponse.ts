/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TaskItemResponse } from './TaskItemResponse';
/**
 * 任务列表响应（包含统计信息）
 */
export type TaskListResponse = {
    /**
     * 任务列表
     */
    tasks: Array<TaskItemResponse>;
    /**
     * 总任务数
     */
    total: number;
    /**
     * 待处理任务数
     */
    pending_count?: number;
    /**
     * 处理中任务数
     */
    processing_count?: number;
    /**
     * 已完成任务数
     */
    completed_count?: number;
    /**
     * 失败任务数
     */
    failed_count?: number;
};

