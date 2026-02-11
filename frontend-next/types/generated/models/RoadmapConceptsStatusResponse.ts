/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConceptStatusResponse } from './ConceptStatusResponse';
/**
 * Roadmap 所有 Concept 状态响应
 *
 * 用于批量查询某 roadmap 的所有 Concept 状态。
 */
export type RoadmapConceptsStatusResponse = {
    /**
     * 路线图 ID
     */
    roadmap_id: string;
    /**
     * 总概念数
     */
    total_concepts: number;
    /**
     * 已完成数量
     */
    completed_count: number;
    /**
     * 概念状态列表
     */
    concepts: Array<ConceptStatusResponse>;
};

