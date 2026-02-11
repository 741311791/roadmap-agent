/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Checkpoint信息Schema（用于调试和前端展示）
 */
export type CheckpointInfo = {
    /**
     * Checkpoint ID
     */
    checkpoint_id: string;
    /**
     * 创建时间
     */
    timestamp: string;
    /**
     * 执行的节点名称
     */
    node_name: string;
    /**
     * 下一步要执行的节点列表
     */
    next_nodes: Array<string>;
    /**
     * 是否可以从此checkpoint重试
     */
    can_retry: boolean;
};

