/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MainGraphNode } from './MainGraphNode';
import type { RetryMode } from './RetryMode';
/**
 * 统一的重试请求Schema
 *
 * 支持两种模式：
 * 1. mode=resume：断点续传（从最后checkpoint恢复）
 * 2. mode=time_travel + target_node：时间旅行（回到指定主图节点）
 */
export type RetryRequest = {
    /**
     * 重试模式：resume（断点续传）或 time_travel（时间旅行）
     */
    mode?: RetryMode;
    /**
     * 目标主图节点（仅当mode=time_travel时有效）
     */
    target_node?: (MainGraphNode | null);
    /**
     * 重试原因（用于日志记录和审计）
     */
    reason?: (string | null);
};

