/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TaskStatus } from '../constants';
/**
 * Celery Worker 信息
 *
 * Args:
 * hostname: Worker 主机名
 * status: Worker 状态
 * active_tasks: 活跃任务数
 * processed_tasks: 已处理任务数
 */
export type CeleryWorkerInfo = {
    /**
     * Worker 主机名
     */
    hostname: string;
    /**
     * Worker 状态
     */
    status: TaskStatus;
    /**
     * 活跃任务数
     */
    active_tasks: number;
    /**
     * 已处理任务数
     */
    processed_tasks?: (number | null);
};

