/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { app__schemas__user__StageSummary } from './app__schemas__user__StageSummary';
/**
 * 路线图历史项
 */
export type RoadmapHistoryItem = {
    roadmap_id: string;
    title: string;
    created_at: string;
    total_concepts: number;
    completed_concepts: number;
    topic?: (string | null);
    status?: (string | null);
    stages?: (Array<app__schemas__user__StageSummary> | null);
    task_id?: (string | null);
    task_status?: (string | null);
    current_step?: (string | null);
    deleted_at?: (string | null);
    deleted_by?: (string | null);
};

