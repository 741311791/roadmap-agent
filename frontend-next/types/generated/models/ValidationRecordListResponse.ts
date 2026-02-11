/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ValidationRecordResponse } from './ValidationRecordResponse';
/**
 * 验证记录列表响应
 *
 * 包含多条验证记录和总数统计。
 */
export type ValidationRecordListResponse = {
    /**
     * 验证记录列表
     */
    records: Array<ValidationRecordResponse>;
    /**
     * 总记录数
     */
    total: number;
};

