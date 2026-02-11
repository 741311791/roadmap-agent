/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 路线图对比响应
 *
 * 用于展示路线图不同版本之间的差异。
 */
export type RoadmapComparisonResponse = {
    /**
     * 任务ID
     */
    task_id: string;
    /**
     * 当前版本号
     */
    current_version: number;
    /**
     * 前一版本号
     */
    previous_version: number;
    /**
     * 对比详情（结构化差异数据）
     */
    comparison: Record<string, any>;
};

