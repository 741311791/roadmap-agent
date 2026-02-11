/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ResponseSchemaModel } from '../models/ResponseSchemaModel';
import type { ResponseSchemaModel_ExecutionLogListResponse_ } from '../models/ResponseSchemaModel_ExecutionLogListResponse_';
import type { ResponseSchemaModel_TraceSummaryResponse_ } from '../models/ResponseSchemaModel_TraceSummaryResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TaskTraceService {
    /**
     * Get Logs
     * 获取指定任务的执行日志
     *
     * 用于查询路线图生成过程的详细日志，支持按日志级别和分类过滤。
     *
     * 权限控制：
     * - 普通用户只能查看自己的任务日志
     * - 超级管理员可以查看所有任务日志
     *
     * Args:
     * task_id: 任务ID
     * db: 数据库会话
     * current_user: 当前登录用户
     * service: 日志追踪服务
     * level: 日志级别筛选（可选）
     * category: 日志分类筛选（可选）
     * limit: 返回数量限制
     * offset: 分页偏移
     *
     * Returns:
     * 日志列表和分页信息
     *
     * Raises:
     * NotFoundError: 任务不存在
     * ForbiddenError: 无权限查看此任务的日志
     * @returns ResponseSchemaModel_ExecutionLogListResponse_ Successful Response
     * @throws ApiError
     */
    public static getLogsApiV1TasksTaskIdLogsGet({
        taskId,
        level,
        category,
        limit = 100,
        offset,
    }: {
        taskId: string,
        level?: (string | null),
        category?: (string | null),
        limit?: number,
        offset?: number,
    }): CancelablePromise<ResponseSchemaModel_ExecutionLogListResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/tasks/{task_id}/logs',
            path: {
                'task_id': taskId,
            },
            query: {
                'level': level,
                'category': category,
                'limit': limit,
                'offset': offset,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Summary
     * 获取执行日志摘要统计
     *
     * 提供任务的整体日志统计信息，包括:
     * - 日志级别分布
     * - 日志分类分布
     * - 总耗时
     * - 时间范围
     *
     * 权限控制：
     * - 普通用户只能查看自己的任务日志
     * - 超级管理员可以查看所有任务日志
     *
     * Args:
     * task_id: 任务ID
     * db: 数据库会话
     * current_user: 当前登录用户
     * service: 日志追踪服务
     *
     * Returns:
     * 日志统计摘要
     *
     * Raises:
     * NotFoundError: 任务不存在
     * ForbiddenError: 无权限查看此任务的日志
     * @returns ResponseSchemaModel_TraceSummaryResponse_ Successful Response
     * @throws ApiError
     */
    public static getSummaryApiV1TasksTaskIdSummaryGet({
        taskId,
    }: {
        taskId: string,
    }): CancelablePromise<ResponseSchemaModel_TraceSummaryResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/tasks/{task_id}/summary',
            path: {
                'task_id': taskId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Errors
     * 获取错误日志
     *
     * 仅返回级别为error的日志，用于快速定位问题。
     *
     * 权限控制：
     * - 普通用户只能查看自己的任务日志
     * - 超级管理员可以查看所有任务日志
     *
     * Args:
     * task_id: 任务ID
     * db: 数据库会话
     * current_user: 当前登录用户
     * service: 日志追踪服务
     * limit: 返回数量限制
     *
     * Returns:
     * 错误日志列表
     *
     * Raises:
     * NotFoundError: 任务不存在
     * ForbiddenError: 无权限查看此任务的日志
     * @returns ResponseSchemaModel_ExecutionLogListResponse_ Successful Response
     * @throws ApiError
     */
    public static getErrorsApiV1TasksTaskIdErrorsGet({
        taskId,
        limit = 50,
    }: {
        taskId: string,
        limit?: number,
    }): CancelablePromise<ResponseSchemaModel_ExecutionLogListResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/tasks/{task_id}/errors',
            path: {
                'task_id': taskId,
            },
            query: {
                'limit': limit,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Subgraph Progress
     * 查询子图执行进度（双 Checkpointer 架构）
     *
     * 使用子图 checkpointer 查询当前任务的子图状态：
     * - 已完成的 Concept 数量
     * - 失败的 Concept 列表
     * - 可恢复性（是否可以断点续传）
     *
     * 双 Checkpointer 架构：
     * - 使用 child_checkpointer（命名空间：child_graph）查询子图状态
     * - 与父图状态完全隔离
     * - 支持细粒度的断点续传
     *
     * Args:
     * task_id: 任务ID
     * current_user: 当前用户
     *
     * Returns:
     * 子图进度信息
     *
     * Raises:
     * NotFoundError: 任务不存在
     * ForbiddenError: 无权限查看此任务
     * @returns ResponseSchemaModel Successful Response
     * @throws ApiError
     */
    public static getSubgraphProgressApiV1TasksTaskIdSubgraphProgressGet({
        taskId,
    }: {
        taskId: string,
    }): CancelablePromise<ResponseSchemaModel> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/tasks/{task_id}/subgraph-progress',
            path: {
                'task_id': taskId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
