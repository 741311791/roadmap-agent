/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TaskStatus } from '../constants';
/**
 * 能力分析任务触发响应模型
 */
export type AnalyzeTaskResponse = {
    /**
     * 任务状态: processing
     */
    status: TaskStatus;
    /**
     * Celery任务ID
     */
    task_id: string;
    /**
     * 提示消息
     */
    message: string;
    /**
     * 技术栈名称
     */
    technology: string;
    /**
     * 能力级别
     */
    proficiency: string;
};

