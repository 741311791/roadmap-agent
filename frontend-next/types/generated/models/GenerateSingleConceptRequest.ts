/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 生成单个 Concept 内容请求
 *
 * 用于独立调用单 Concept 子图生成内容。
 */
export type GenerateSingleConceptRequest = {
    /**
     * 概念 ID
     */
    concept_id: string;
    /**
     * 路线图 ID
     */
    roadmap_id: string;
    /**
     * 是否强制重新生成
     */
    force_regenerate?: boolean;
};

