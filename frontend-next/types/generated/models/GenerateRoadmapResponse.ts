/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TaskStatus } from '../constants';
/**
 * 路线图生成响应
 */
export type GenerateRoadmapResponse = {
    /**
     * 任务ID
     */
    task_id: string;
    /**
     * 任务状态（pending/processing/completed/failed）
     */
    status: TaskStatus;
    /**
     * 响应消息
     */
    message: string;
};

