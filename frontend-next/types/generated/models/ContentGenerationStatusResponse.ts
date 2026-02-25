/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TaskStatus } from '../constants';
/**
 * 内容生成状态响应
 */
export type ContentGenerationStatusResponse = {
    /**
     * 任务ID
     */
    task_id: string;
    /**
     * Celery任务ID
     */
    celery_task_id?: (string | null);
    /**
     * Celery任务状态
     */
    status: TaskStatus;
    /**
     * 进度信息
     */
    progress?: (Record<string, any> | null);
    /**
     * 状态消息
     */
    message?: (string | null);
    /**
     * 任务结果
     */
    result?: (Record<string, any> | null);
};

