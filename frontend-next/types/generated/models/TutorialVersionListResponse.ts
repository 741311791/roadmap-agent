/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TutorialItemResponse } from './TutorialItemResponse';
/**
 * 教程版本列表响应
 *
 * 包含概念的所有教程版本历史。
 */
export type TutorialVersionListResponse = {
    /**
     * 路线图ID
     */
    roadmap_id: string;
    /**
     * 概念ID
     */
    concept_id: string;
    /**
     * 总版本数
     */
    total_versions: number;
    /**
     * 教程列表
     */
    tutorials: Array<TutorialItemResponse>;
};

