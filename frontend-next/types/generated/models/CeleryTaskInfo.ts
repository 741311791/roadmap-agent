/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TaskStatus } from '../constants';
/**
 * Celery 任务信息
 *
 * Args:
 * task_id: 任务 ID
 * task_name: 任务名称
 * queue: 队列名称
 * status: 任务状态 (PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED)
 * worker: Worker 名称
 * started_at: 开始时间
 * completed_at: 完成时间
 * duration: 执行耗时（秒）
 * args: 任务参数
 * kwargs: 任务关键字参数
 * result: 任务结果
 * error: 错误信息
 */
export type CeleryTaskInfo = {
    /**
     * 任务 ID
     */
    task_id: string;
    /**
     * 任务名称
     */
    task_name: string;
    /**
     * 队列名称
     */
    queue?: (string | null);
    /**
     * 任务状态
     */
    status: TaskStatus;
    /**
     * Worker 名称
     */
    worker?: (string | null);
    /**
     * 开始时间 (ISO 格式)
     */
    started_at?: (string | null);
    /**
     * 完成时间 (ISO 格式)
     */
    completed_at?: (string | null);
    /**
     * 执行耗时（秒）
     */
    duration?: (number | null);
    /**
     * 任务参数
     */
    args?: null;
    /**
     * 任务关键字参数
     */
    kwargs?: (Record<string, any> | null);
    /**
     * 任务结果
     */
    result?: null;
    /**
     * 错误信息
     */
    error?: (string | null);
};

