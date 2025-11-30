/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { Concept } from './Concept';
/**
 * 第二层：模块
 */
export type Module = {
    module_id: string;
    /**
     * 模块名称，如 'React 核心'
     */
    name: string;
    description: string;
    concepts: Array<Concept>;
};

