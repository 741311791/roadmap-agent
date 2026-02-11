/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CeleryTaskInfo } from './CeleryTaskInfo';
/**
 * Celery 任务列表响应
 *
 * Args:
 * tasks: 任务列表
 * total: 总数
 */
export type CeleryTaskListResponse = {
    /**
     * 任务列表
     */
    tasks: Array<CeleryTaskInfo>;
    /**
     * 总数
     */
    total: number;
};

