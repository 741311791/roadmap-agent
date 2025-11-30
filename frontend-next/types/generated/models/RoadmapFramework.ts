/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Stage } from './Stage';
/**
 * 完整的三层路线图框架
 */
export type RoadmapFramework = {
    roadmap_id: string;
    /**
     * 路线图标题，如 '全栈开发学习路线'
     */
    title: string;
    stages: Array<Stage>;
    total_estimated_hours: number;
    recommended_completion_weeks: number;
};

