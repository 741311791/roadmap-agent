/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 通用响应模型
 *
 * 所有API响应都遵循此格式：
 * {
     * "code": 200,
     * "msg": "Success",
     * "data": { ... }
     * }
     */
    export type ResponseModel = {
        /**
         * HTTP状态码
         */
        code: number;
        /**
         * 响应消息（用户友好）
         */
        msg: string;
        /**
         * 响应数据
         */
        data?: null;
    };

