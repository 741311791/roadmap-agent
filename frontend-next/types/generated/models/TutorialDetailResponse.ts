/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ContentStatus } from '../constants';
import type { TaskStatus } from '../constants';
/**
 * 教程详情响应
 *
 * 单个教程版本的完整信息。
 */
export type TutorialDetailResponse = {
    /**
     * 路线图ID
     */
    roadmap_id: string;
    /**
     * 概念ID
     */
    concept_id: string;
    /**
     * 教程ID
     */
    tutorial_id: string;
    /**
     * 教程标题
     */
    title: string;
    /**
     * 教程摘要
     */
    summary?: (string | null);
    /**
     * 内容URL（S3）
     */
    content_url?: (string | null);
    /**
     * 内容版本号
     */
    content_version: number;
    /**
     * 是否为最新版本
     */
    is_latest: boolean;
    /**
     * 内容生成状态
     */
    content_status: TaskStatus;
    /**
     * 预计完成时间（分钟）
     */
    estimated_completion_time?: (number | null);
    /**
     * 创建时间（ISO格式）
     */
    created_at?: (string | null);
};

