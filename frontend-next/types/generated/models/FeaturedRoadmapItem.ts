/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { app__schemas__featured__StageSummary } from './app__schemas__featured__StageSummary';
/**
 * 精选路线图条目
 */
export type FeaturedRoadmapItem = {
    roadmap_id: string;
    title: string;
    created_at: string;
    total_concepts: number;
    completed_concepts?: number;
    topic?: (string | null);
    status?: string;
    stages?: (Array<app__schemas__featured__StageSummary> | null);
};

