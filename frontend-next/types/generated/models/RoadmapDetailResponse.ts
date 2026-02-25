/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { WorkflowStep } from '../constants';
import type { TaskStatus } from '../constants';
/**
 * 路线图详情响应
 */
export type RoadmapDetailResponse = {
    /**
     * 路线图ID
     */
    roadmap_id: string;
    /**
     * 用户ID
     */
    user_id: string;
    /**
     * 学习目标
     */
    learning_goal: string;
    /**
     * 创建时间
     */
    created_at: string;
    /**
     * 更新时间
     */
    updated_at: string;
    /**
     * 路线图框架数据（生成中时为None）
     */
    framework?: (Record<string, any> | null);
    /**
     * 路线图状态
     */
    status: TaskStatus;
    /**
     * 标题
     */
    title?: (string | null);
    /**
     * 描述
     */
    description?: (string | null);
    /**
     * 任务ID（生成中时有值）
     */
    task_id?: (string | null);
    /**
     * 当前步骤（生成中时有值）
     */
    current_step?: (string | null);
    /**
     * 状态消息（生成中时有值）
     */
    message?: (string | null);
};

