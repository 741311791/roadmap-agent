/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 追踪摘要响应
 *
 * 任务的日志统计信息。
 */
export type TraceSummaryResponse = {
    /**
     * 任务ID
     */
    task_id: string;
    /**
     * 按日志级别统计
     */
    level_stats: Record<string, number>;
    /**
     * 按分类统计
     */
    category_stats: Record<string, number>;
    /**
     * 总耗时（毫秒）
     */
    total_duration_ms: number;
    /**
     * 首条日志时间
     */
    first_log_at?: (string | null);
    /**
     * 末条日志时间
     */
    last_log_at?: (string | null);
    /**
     * 总日志数
     */
    total_logs: number;
};

