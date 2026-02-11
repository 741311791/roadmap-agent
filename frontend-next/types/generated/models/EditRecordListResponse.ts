/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { EditRecordResponse } from './EditRecordResponse';
/**
 * 编辑记录列表响应
 *
 * 包含多条编辑记录和总数统计。
 */
export type EditRecordListResponse = {
    /**
     * 编辑记录列表
     */
    records: Array<EditRecordResponse>;
    /**
     * 总记录数
     */
    total: number;
};

