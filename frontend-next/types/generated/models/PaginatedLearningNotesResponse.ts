/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { LearningNoteResponse } from './LearningNoteResponse';
/**
 * 分页笔记列表响应
 */
export type PaginatedLearningNotesResponse = {
    notes: Array<LearningNoteResponse>;
    total: number;
    page?: number;
    page_size?: number;
};

