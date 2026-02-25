/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TaskStatus } from '../constants';
/**
 * 快速检查路线图状态响应
 */
export type RoadmapStatusQuickResponse = {
    /**
     * 路线图ID
     */
    roadmap_id: string;
    /**
     * 路线图状态
     */
    status: TaskStatus;
    /**
     * 是否有活跃任务
     */
    has_active_task: boolean;
    /**
     * 活跃任务ID
     */
    active_task_id?: (string | null);
    /**
     * 僵尸概念ID列表
     */
    zombie_concepts?: (Array<string> | null);
    /**
     * 僵尸概念数量
     */
    zombie_count?: number;
};

