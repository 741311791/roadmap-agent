/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 知识缺口模型
 */
export type KnowledgeGap = {
    /**
     * 主题名称
     */
    topic: string;
    /**
     * 详细说明
     */
    description: string;
    /**
     * 优先级: high/medium/low
     */
    priority: string;
    /**
     * 学习建议列表
     */
    recommendations: Array<string>;
};

