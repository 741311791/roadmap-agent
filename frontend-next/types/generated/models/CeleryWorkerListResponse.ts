/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CeleryWorkerInfo } from './CeleryWorkerInfo';
/**
 * Celery Worker 列表响应
 *
 * Args:
 * workers: Worker 列表
 * total: 总数
 */
export type CeleryWorkerListResponse = {
    /**
     * Worker 列表
     */
    workers: Array<CeleryWorkerInfo>;
    /**
     * 总数
     */
    total: number;
};

