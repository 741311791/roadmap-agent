/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 第三层：概念/知识点（轻量级结构，不嵌套详细内容）
 */
export type Concept = {
    concept_id: string;
    /**
     * 概念名称，如 'React Hooks 原理'
     */
    name: string;
    /**
     * 简短描述（1-2 句话）
     */
    description: string;
    /**
     * 预估学习时长（小时）
     */
    estimated_hours: number;
    /**
     * 前置概念 ID 列表
     */
    prerequisites?: Array<string>;
    difficulty?: 'easy' | 'medium' | 'hard';
    /**
     * 关键词标签
     */
    keywords?: Array<string>;
    /**
     * 教程内容生成状态
     */
    content_status?: 'pending' | 'generating' | 'completed' | 'failed';
    /**
     * 指向 S3 Key 或内容 API 的 ID，如 's3://bucket/{roadmap_id}/concepts/{concept_id}/v1.md'
     */
    content_ref?: (string | null);
    /**
     * 内容版本号
     */
    content_version?: string;
    /**
     * 教程摘要（用于前端预览，避免加载完整内容）
     */
    content_summary?: (string | null);
    /**
     * 资源推荐生成状态
     */
    resources_status?: 'pending' | 'generating' | 'completed' | 'failed';
    /**
     * 资源推荐记录 ID（UUID 格式，关联 resource_recommendation_metadata 表）
     */
    resources_id?: (string | null);
    /**
     * 推荐资源数量
     */
    resources_count?: number;
    /**
     * 测验生成状态
     */
    quiz_status?: 'pending' | 'generating' | 'completed' | 'failed';
    /**
     * 测验 ID（UUID 格式）
     */
    quiz_id?: (string | null);
    /**
     * 测验题目数量
     */
    quiz_questions_count?: number;
};

