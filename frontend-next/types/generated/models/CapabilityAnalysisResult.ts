/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { KnowledgeGap } from './KnowledgeGap';
import type { ProficiencyVerification } from './ProficiencyVerification';
import type { ScoreBreakdownItem } from './ScoreBreakdownItem';
/**
 * 能力分析结果模型
 */
export type CapabilityAnalysisResult = {
    /**
     * 技术栈名称
     */
    technology: string;
    /**
     * 声称的能力级别
     */
    proficiency_level: string;
    /**
     * 整体评价
     */
    overall_assessment: string;
    /**
     * 优势领域列表
     */
    strengths: Array<string>;
    /**
     * 薄弱点列表
     */
    weaknesses: Array<string>;
    /**
     * 知识缺口列表
     */
    knowledge_gaps: Array<KnowledgeGap>;
    /**
     * 学习建议列表
     */
    learning_suggestions: Array<string>;
    /**
     * 能力级别验证
     */
    proficiency_verification: ProficiencyVerification;
    /**
     * 各难度得分情况
     */
    score_breakdown: Record<string, ScoreBreakdownItem>;
};

