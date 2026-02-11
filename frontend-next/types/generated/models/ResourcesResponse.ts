/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 资源推荐响应
 *
 * 概念的学习资源推荐信息。
 */
export type ResourcesResponse = {
    /**
     * 路线图ID
     */
    roadmap_id: string;
    /**
     * 概念ID
     */
    concept_id: string;
    /**
     * 资源记录ID
     */
    resources_id: string;
    /**
     * 资源列表
     */
    resources: Array<Record<string, any>>;
    /**
     * 资源数量
     */
    resources_count: number;
    /**
     * 使用的搜索查询
     */
    search_queries_used?: (Array<string> | null);
    /**
     * 创建时间（ISO格式）
     */
    created_at?: (string | null);
};

