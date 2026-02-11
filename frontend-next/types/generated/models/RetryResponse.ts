/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { RetryScope } from './RetryScope';
/**
 * 重试响应Schema
 */
export type RetryResponse = {
    /**
     * 重试是否成功启动
     */
    success: boolean;
    /**
     * 响应消息
     */
    message: string;
    /**
     * 任务ID
     */
    task_id: string;
    /**
     * 新的Celery任务ID（如果创建了新任务）
     */
    celery_task_id?: (string | null);
    /**
     * 实际执行的重试范围
     */
    retry_scope: RetryScope;
    /**
     * 从哪个节点/阶段开始重试
     */
    retry_from?: (string | null);
};

