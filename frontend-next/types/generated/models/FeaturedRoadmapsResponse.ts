/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { FeaturedRoadmapItem } from './FeaturedRoadmapItem';
/**
 * 精选路线图列表响应
 */
export type FeaturedRoadmapsResponse = {
    roadmaps: Array<FeaturedRoadmapItem>;
    total: number;
    featured_user_id: string;
    featured_user_email: string;
};

