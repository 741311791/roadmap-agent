/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Module } from './Module';
/**
 * 第一层：阶段
 */
export type Stage = {
    stage_id: string;
    /**
     * 阶段名称，如 '前端基础'
     */
    name: string;
    description: string;
    /**
     * 阶段顺序
     */
    order: number;
    modules: Array<Module>;
};

