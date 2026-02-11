/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 能力级别验证模型
 */
export type ProficiencyVerification = {
    /**
     * 声称的能力级别
     */
    claimed_level: string;
    /**
     * 验证的实际能力级别
     */
    verified_level: string;
    /**
     * 置信度: high/medium/low
     */
    confidence: string;
    /**
     * 判定依据
     */
    reasoning: string;
};

