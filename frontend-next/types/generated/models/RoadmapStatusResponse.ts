/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TaskStatus } from '../constants';
/**
 * 路线图状态响应
 */
export type RoadmapStatusResponse = {
    /**
     * 路线图ID
     */
    roadmap_id: string;
    /**
     * 路线图状态
     */
    status: TaskStatus;
    /**
     * 关联任务ID
     */
    task_id?: (string | null);
};

