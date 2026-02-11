/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ResponseSchemaModel } from '../models/ResponseSchemaModel';
import type { ResponseSchemaModel_EditRecordListResponse_ } from '../models/ResponseSchemaModel_EditRecordListResponse_';
import type { ResponseSchemaModel_EditRecordResponse_ } from '../models/ResponseSchemaModel_EditRecordResponse_';
import type { ResponseSchemaModel_IntentAnalysisResponse_ } from '../models/ResponseSchemaModel_IntentAnalysisResponse_';
import type { ResponseSchemaModel_RoadmapComparisonResponse_ } from '../models/ResponseSchemaModel_RoadmapComparisonResponse_';
import type { ResponseSchemaModel_ValidationRecordListResponse_ } from '../models/ResponseSchemaModel_ValidationRecordListResponse_';
import type { ResponseSchemaModel_ValidationRecordResponse_ } from '../models/ResponseSchemaModel_ValidationRecordResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RoadmapMetadataService {
    /**
     * Get Intent Analysis
     * 获取指定路线图的需求分析元数据
     *
     * 状态处理：
     * - 数据已生成: 返回完整数据
     * - 任务执行中: 返回任务状态 (available=False)
     * - 任务不存在: 返回 404
     *
     * Args:
     * roadmap_id: 路线图ID
     * db: 数据库会话
     *
     * Returns:
     * 需求分析元数据或任务状态
     *
     * Raises:
     * NotFoundError: 需求分析元数据不存在
     * @returns ResponseSchemaModel_IntentAnalysisResponse_ Successful Response
     * @throws ApiError
     */
    public static getIntentAnalysisApiV1RoadmapsRoadmapIdIntentAnalysisGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<ResponseSchemaModel_IntentAnalysisResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/roadmaps/{roadmap_id}/intent-analysis',
            path: {
                'roadmap_id': roadmapId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Latest Edit Record
     * 获取最新的编辑记录
     *
     * Args:
     * roadmap_id: 路线图ID
     * db: 数据库会话
     *
     * Returns:
     * 最新版本的编辑记录
     *
     * Raises:
     * NotFoundError: 没有找到编辑记录
     * @returns ResponseSchemaModel_EditRecordResponse_ Successful Response
     * @throws ApiError
     */
    public static getLatestEditRecordApiV1RoadmapsRoadmapIdEditRecordsLatestGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<ResponseSchemaModel_EditRecordResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/roadmaps/{roadmap_id}/edit-records/latest',
            path: {
                'roadmap_id': roadmapId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get All Edit Records
     * 获取所有编辑记录
     *
     * Args:
     * roadmap_id: 路线图ID
     * db: 数据库会话
     *
     * Returns:
     * 编辑记录列表（按版本号降序）
     * @returns ResponseSchemaModel_EditRecordListResponse_ Successful Response
     * @throws ApiError
     */
    public static getAllEditRecordsApiV1RoadmapsRoadmapIdEditRecordsGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<ResponseSchemaModel_EditRecordListResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/roadmaps/{roadmap_id}/edit-records',
            path: {
                'roadmap_id': roadmapId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Roadmap Comparison
     * 获取路线图版本对比
     *
     * 对比当前版本与前一版本的差异。
     *
     * Args:
     * roadmap_id: 路线图ID
     * db: 数据库会话
     *
     * Returns:
     * 版本对比详情
     *
     * Raises:
     * NotFoundError: 没有足够的版本进行对比（至少需要2个版本）
     * @returns ResponseSchemaModel_RoadmapComparisonResponse_ Successful Response
     * @throws ApiError
     */
    public static getRoadmapComparisonApiV1RoadmapsRoadmapIdComparisonGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<ResponseSchemaModel_RoadmapComparisonResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/roadmaps/{roadmap_id}/comparison',
            path: {
                'roadmap_id': roadmapId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Latest Validation Record
     * 获取最新的验证记录
     *
     * Args:
     * roadmap_id: 路线图ID
     * db: 数据库会话
     *
     * Returns:
     * 最新版本的验证记录
     *
     * Raises:
     * NotFoundError: 没有找到验证记录
     * @returns ResponseSchemaModel_ValidationRecordResponse_ Successful Response
     * @throws ApiError
     */
    public static getLatestValidationRecordApiV1RoadmapsRoadmapIdValidationRecordsLatestGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<ResponseSchemaModel_ValidationRecordResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/roadmaps/{roadmap_id}/validation-records/latest',
            path: {
                'roadmap_id': roadmapId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get All Validation Records
     * 获取所有验证记录
     *
     * Args:
     * roadmap_id: 路线图ID
     * db: 数据库会话
     *
     * Returns:
     * 验证记录列表（按版本号降序）
     * @returns ResponseSchemaModel_ValidationRecordListResponse_ Successful Response
     * @throws ApiError
     */
    public static getAllValidationRecordsApiV1RoadmapsRoadmapIdValidationRecordsGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<ResponseSchemaModel_ValidationRecordListResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/roadmaps/{roadmap_id}/validation-records',
            path: {
                'roadmap_id': roadmapId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Edit History Full
     * 获取完整编辑历史（包含详细diff和修改内容）
     *
     * 返回路线图的所有编辑记录，包括：
     * - 编辑来源（validation失败/人工反馈）
     * - 修改内容详情
     * - diff摘要
     * - 关联的编辑计划
     *
     * Args:
     * roadmap_id: 路线图ID
     * db: 数据库会话
     *
     * Returns:
     * 完整编辑历史列表（按时间倒序）
     *
     * Example:
     * {
         * "success": true,
         * "data": {
             * "roadmap_id": "xxx",
             * "edit_history": [
                 * {
                     * "id": 1,
                     * "timestamp": "2026-01-23T12:00:00Z",
                     * "edit_source": "validation_failed",
                     * "edit_plan_id": "xxx",
                     * "changes_made": {...},
                     * "diff_summary": "修改了3个模块...",
                     * "version": 2
                     * }
                     * ],
                     * "total": 3
                     * }
                     * }
                     * @returns ResponseSchemaModel Successful Response
                     * @throws ApiError
                     */
                    public static getEditHistoryFullApiV1RoadmapsRoadmapIdEditHistoryFullGet({
                        roadmapId,
                    }: {
                        roadmapId: string,
                    }): CancelablePromise<ResponseSchemaModel> {
                        return __request(OpenAPI, {
                            method: 'GET',
                            url: '/api/v1/roadmaps/{roadmap_id}/edit/history-full',
                            path: {
                                'roadmap_id': roadmapId,
                            },
                            errors: {
                                422: `Validation Error`,
                            },
                        });
                    }
                }
