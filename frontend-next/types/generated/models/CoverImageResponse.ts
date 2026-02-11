/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { TaskStatus } from '../constants';
/**
 * 封面图响应模型
 *
 * 用于单个路线图封面图查询。
 */
export type CoverImageResponse = {
    /**
     * 路线图 ID
     */
    roadmap_id: string;
    /**
     * 封面图 URL
     */
    cover_image_url?: (string | null);
    /**
     * 状态: not_started/pending/generating/success/failed
     */
    status: TaskStatus;
    /**
     * 错误信息
     */
    error?: (string | null);
    /**
     * 重试次数
     */
    retry_count?: (number | null);
};

