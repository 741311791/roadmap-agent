/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ExecutionLogResponse } from './ExecutionLogResponse';
/**
 * 执行日志列表响应
 *
 * 包含多条日志和分页信息。
 */
export type ExecutionLogListResponse = {
    /**
     * 日志列表
     */
    logs: Array<ExecutionLogResponse>;
    /**
     * 总日志数
     */
    total: number;
    /**
     * 分页偏移
     */
    offset: number;
    /**
     * 每页数量
     */
    limit: number;
};

