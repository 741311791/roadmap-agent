/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CheckpointInfo } from './CheckpointInfo';
import type { RetryMode } from './RetryMode';
/**
 * 任务重试状态Schema
 *
 * 提供任务当前状态和可用的重试模式信息
 */
export type TaskRetryStatus = {
    task_id: string;
    /**
     * 当前是否可以重试
     */
    can_retry: boolean;
    /**
     * 如果不能重试，说明原因
     */
    retry_reason?: (string | null);
    /**
     * 当前主图的checkpoint信息
     */
    current_checkpoint?: (CheckpointInfo | null);
    /**
     * 是否有子图在中断状态（需要特殊处理）
     */
    is_subgraph_interrupted?: boolean;
    /**
     * 可用的重试模式
     */
    available_modes: Array<RetryMode>;
};

