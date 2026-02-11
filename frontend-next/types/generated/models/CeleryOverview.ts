/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * Celery 任务队列总览
 *
 * Args:
 * active_count: 活跃任务数
 * pending_count: 待处理任务数（预约+保留）
 * scheduled_count: 预约任务数
 * reserved_count: 保留任务数
 * queue_lengths: 各队列长度统计
 * workers: Worker 列表
 */
export type CeleryOverview = {
    /**
     * 活跃任务数
     */
    active_count: number;
    /**
     * 待处理任务数
     */
    pending_count: number;
    /**
     * 预约任务数
     */
    scheduled_count: number;
    /**
     * 保留任务数
     */
    reserved_count: number;
    /**
     * 各队列长度统计
     */
    queue_lengths: Record<string, number>;
    /**
     * Worker 列表
     */
    workers: Array<string>;
};

