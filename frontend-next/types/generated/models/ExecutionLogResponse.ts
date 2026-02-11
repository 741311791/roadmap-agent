/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 执行日志响应
 *
 * 单条执行日志的完整信息。
 */
export type ExecutionLogResponse = {
    /**
     * 日志ID
     */
    id: string;
    /**
     * 任务ID
     */
    task_id: string;
    /**
     * 路线图ID
     */
    roadmap_id?: (string | null);
    /**
     * 概念ID
     */
    concept_id?: (string | null);
    /**
     * 日志级别（info/warning/error）
     */
    level: string;
    /**
     * 日志分类（agent/system/validation等）
     */
    category: string;
    /**
     * 执行步骤
     */
    step?: (string | null);
    /**
     * Agent名称
     */
    agent_name?: (string | null);
    /**
     * 日志消息
     */
    message: string;
    /**
     * 详细信息（JSON格式）
     */
    details?: (Record<string, any> | null);
    /**
     * 耗时（毫秒）
     */
    duration_ms?: (number | null);
    /**
     * 创建时间（ISO格式）
     */
    created_at: string;
};

