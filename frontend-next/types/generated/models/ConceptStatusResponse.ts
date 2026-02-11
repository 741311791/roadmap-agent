/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContentStatus } from '../constants';
import type { TaskStatus } from '../constants';
/**
 * 单个 Concept 状态响应
 *
 * 用于查询 Concept 内容生成状态。
 */
export type ConceptStatusResponse = {
    /**
     * 概念 ID
     */
    concept_id: string;
    /**
     * 整体状态
     */
    overall_status: TaskStatus;
    /**
     * 教程状态
     */
    tutorial_status: TaskStatus;
    /**
     * 资源状态
     */
    resources_status: TaskStatus;
    /**
     * 测验状态
     */
    quiz_status: TaskStatus;
    /**
     * 教程 ID
     */
    tutorial_id?: (string | null);
    /**
     * 资源 ID
     */
    resources_id?: (string | null);
    /**
     * 测验 ID
     */
    quiz_id?: (string | null);
    /**
     * 全部内容完成时间 (ISO 格式)
     */
    all_content_completed_at?: (string | null);
};

