/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { BatchCoverImageResponse } from '../models/BatchCoverImageResponse';
import type { BatchGenerateRequest } from '../models/BatchGenerateRequest';
import type { BatchGetCoverImagesRequest } from '../models/BatchGetCoverImagesRequest';
import type { ChatModificationRequest } from '../models/ChatModificationRequest';
import type { CoverImageResponse } from '../models/CoverImageResponse';
import type { FeaturedRoadmapsResponse } from '../models/FeaturedRoadmapsResponse';
import type { ResponseSchemaModel } from '../models/ResponseSchemaModel';
import type { ResponseSchemaModel_EditRecordListResponse_ } from '../models/ResponseSchemaModel_EditRecordListResponse_';
import type { ResponseSchemaModel_EditRecordResponse_ } from '../models/ResponseSchemaModel_EditRecordResponse_';
import type { ResponseSchemaModel_IntentAnalysisResponse_ } from '../models/ResponseSchemaModel_IntentAnalysisResponse_';
import type { ResponseSchemaModel_RoadmapComparisonResponse_ } from '../models/ResponseSchemaModel_RoadmapComparisonResponse_';
import type { ResponseSchemaModel_RoadmapDeleteResponse_ } from '../models/ResponseSchemaModel_RoadmapDeleteResponse_';
import type { ResponseSchemaModel_RoadmapHistoryResponse_ } from '../models/ResponseSchemaModel_RoadmapHistoryResponse_';
import type { ResponseSchemaModel_RoadmapPermanentDeleteResponse_ } from '../models/ResponseSchemaModel_RoadmapPermanentDeleteResponse_';
import type { ResponseSchemaModel_RoadmapRestoreResponse_ } from '../models/ResponseSchemaModel_RoadmapRestoreResponse_';
import type { ResponseSchemaModel_RoadmapStatusQuickResponse_ } from '../models/ResponseSchemaModel_RoadmapStatusQuickResponse_';
import type { ResponseSchemaModel_RoadmapStatusResponse_ } from '../models/ResponseSchemaModel_RoadmapStatusResponse_';
import type { ResponseSchemaModel_ValidationRecordListResponse_ } from '../models/ResponseSchemaModel_ValidationRecordListResponse_';
import type { ResponseSchemaModel_ValidationRecordResponse_ } from '../models/ResponseSchemaModel_ValidationRecordResponse_';
import type { UserRequest } from '../models/UserRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RoadmapResourcesService {
    /**
     * Get User Roadmaps
     * 获取当前用户的路线图列表（只包括已生成完成的路线图）
     *
     * Args:
     * db: 数据库会话
     * current_user: 当前用户（从JWT提取）
     * service: 用户服务
     * limit: 返回数量限制（默认50）
     * offset: 分页偏移（默认0）
     *
     * Returns:
     * 用户的路线图列表（从 roadmap_metadata 表查询）
     *
     * Note:
     * 学习进度从 concept_progress 表获取，而不是 content_status 字段。
     * content_status 表示内容生成状态，concept_progress 表示用户学习进度。
     *
     * Example:
     * ```json
     * {
         * "code": 200,
         * "msg": "Success",
         * "data": {
             * "roadmaps": [
                 * {
                     * "roadmap_id": "python-guide-xxx",
                     * "title": "Python Web Development",
                     * "created_at": "2024-01-01T00:00:00Z",
                     * "total_concepts": 20,
                     * "completed_concepts": 5,
                     * "topic": "python web development",
                     * "status": "learning"
                     * }
                     * ],
                     * "total": 1,
                     * "in_progress_count": 0
                     * }
                     * }
                     * ```
                     * @returns ResponseSchemaModel_RoadmapHistoryResponse_ Successful Response
                     * @throws ApiError
                     */
                    public static getUserRoadmapsApiV1RoadmapsMyGet({
                        limit = 50,
                        offset,
                    }: {
                        limit?: number,
                        offset?: number,
                    }): CancelablePromise<ResponseSchemaModel_RoadmapHistoryResponse_> {
                        return __request(OpenAPI, {
                            method: 'GET',
                            url: '/api/v1/roadmaps/my',
                            query: {
                                'limit': limit,
                                'offset': offset,
                            },
                            errors: {
                                422: `Validation Error`,
                            },
                        });
                    }
                    /**
                     * Get Deleted Roadmaps
                     * 获取当前用户回收站中的路线图列表
                     *
                     * Args:
                     * db: 数据库会话
                     * current_user: 当前用户（从JWT提取）
                     * service: 用户服务
                     * limit: 返回数量限制（默认50）
                     * offset: 分页偏移（默认0）
                     *
                     * Returns:
                     * 回收站中的路线图列表，按删除时间降序排列
                     *
                     * Example:
                     * ```json
                     * {
                         * "code": 200,
                         * "msg": "Success",
                         * "data": {
                             * "roadmaps": [
                                 * {
                                     * "roadmap_id": "python-guide-xxx",
                                     * "title": "Python Web Development",
                                     * "created_at": "2024-01-01T00:00:00Z",
                                     * "total_concepts": 20,
                                     * "completed_concepts": 5,
                                     * "topic": "python web development",
                                     * "status": "deleted",
                                     * "deleted_at": "2024-01-15T00:00:00Z",
                                     * "deleted_by": "user-123"
                                     * }
                                     * ],
                                     * "total": 1,
                                     * "in_progress_count": 0
                                     * }
                                     * }
                                     * ```
                                     * @returns ResponseSchemaModel_RoadmapHistoryResponse_ Successful Response
                                     * @throws ApiError
                                     */
                                    public static getDeletedRoadmapsApiV1RoadmapsTrashGet({
                                        limit = 50,
                                        offset,
                                    }: {
                                        limit?: number,
                                        offset?: number,
                                    }): CancelablePromise<ResponseSchemaModel_RoadmapHistoryResponse_> {
                                        return __request(OpenAPI, {
                                            method: 'GET',
                                            url: '/api/v1/roadmaps/trash',
                                            query: {
                                                'limit': limit,
                                                'offset': offset,
                                            },
                                            errors: {
                                                422: `Validation Error`,
                                            },
                                        });
                                    }
                                    /**
                                     * Get Featured Roadmaps
                                     * 获取精选路线图列表
                                     *
                                     * 从配置的Featured User (admin@example.com) 获取已完成的路线图，
                                     * 用于首页Featured Roadmaps模块展示。
                                     *
                                     * Args:
                                     * limit: 返回数量限制（默认50）
                                     * offset: 分页偏移（默认0）
                                     * db: 数据库会话
                                     *
                                     * Returns:
                                     * 精选路线图列表（只包含已完成且未删除的路线图）
                                     *
                                     * Raises:
                                     * HTTPException: 404 - Featured用户不存在
                                     *
                                     * Example:
                                     * ```json
                                     * {
                                         * "roadmaps": [
                                             * {
                                                 * "roadmap_id": "roadmap-001",
                                                 * "title": "Python Web Development",
                                                 * "created_at": "2024-01-01T00:00:00",
                                                 * "total_concepts": 28,
                                                 * "completed_concepts": 0,
                                                 * "topic": "python web",
                                                 * "status": "completed"
                                                 * }
                                                 * ],
                                                 * "total": 1,
                                                 * "featured_user_id": "user-001",
                                                 * "featured_user_email": "admin@example.com"
                                                 * }
                                                 * ```
                                                 * @returns FeaturedRoadmapsResponse Successful Response
                                                 * @throws ApiError
                                                 */
                                                public static getFeaturedRoadmapsApiV1RoadmapsFeaturedGet({
                                                    limit = 50,
                                                    offset,
                                                }: {
                                                    limit?: number,
                                                    offset?: number,
                                                }): CancelablePromise<FeaturedRoadmapsResponse> {
                                                    return __request(OpenAPI, {
                                                        method: 'GET',
                                                        url: '/api/v1/roadmaps/featured',
                                                        query: {
                                                            'limit': limit,
                                                            'offset': offset,
                                                        },
                                                        errors: {
                                                            422: `Validation Error`,
                                                        },
                                                    });
                                                }
                                                /**
                                                 * Delete Roadmap
                                                 * 删除路线图（软删除）
                                                 *
                                                 * 根据 roadmap_id 格式自动判断删除方式：
                                                 * 1. task-前缀：物理删除任务记录
                                                 * 2. 普通格式：软删除路线图（移到回收站）
                                                 *
                                                 * Args:
                                                 * roadmap_id: 路线图 ID
                                                 * db: 数据库会话（自动commit/rollback）
                                                 * current_user: 当前用户（从JWT获取，防止伪造）
                                                 * service: 管理服务
                                                 *
                                                 * Returns:
                                                 * 删除结果
                                                 *
                                                 * Raises:
                                                 * NotFoundError: 路线图不存在
                                                 * ForbiddenError: 无权限删除此路线图
                                                 * InternalServerError: 删除失败
                                                 * @returns ResponseSchemaModel_RoadmapDeleteResponse_ Successful Response
                                                 * @throws ApiError
                                                 */
                                                public static deleteRoadmapApiV1RoadmapsRoadmapIdDelete({
                                                    roadmapId,
                                                }: {
                                                    roadmapId: string,
                                                }): CancelablePromise<ResponseSchemaModel_RoadmapDeleteResponse_> {
                                                    return __request(OpenAPI, {
                                                        method: 'DELETE',
                                                        url: '/api/v1/roadmaps/{roadmap_id}',
                                                        path: {
                                                            'roadmap_id': roadmapId,
                                                        },
                                                        errors: {
                                                            422: `Validation Error`,
                                                        },
                                                    });
                                                }
                                                /**
                                                 * Get Roadmap Status
                                                 * 获取路线图状态
                                                 *
                                                 * Args:
                                                 * roadmap_id: 路线图 ID
                                                 * db: 数据库会话
                                                 * service: 状态服务
                                                 *
                                                 * Returns:
                                                 * 路线图状态信息（roadmap_id、status、task_id）
                                                 *
                                                 * Raises:
                                                 * NotFoundError: 路线图不存在
                                                 * @returns ResponseSchemaModel_RoadmapStatusResponse_ Successful Response
                                                 * @throws ApiError
                                                 */
                                                public static getRoadmapStatusApiV1RoadmapsRoadmapIdStatusGet({
                                                    roadmapId,
                                                }: {
                                                    roadmapId: string,
                                                }): CancelablePromise<ResponseSchemaModel_RoadmapStatusResponse_> {
                                                    return __request(OpenAPI, {
                                                        method: 'GET',
                                                        url: '/api/v1/roadmaps/{roadmap_id}/status',
                                                        path: {
                                                            'roadmap_id': roadmapId,
                                                        },
                                                        errors: {
                                                            422: `Validation Error`,
                                                        },
                                                    });
                                                }
                                                /**
                                                 * Check Roadmap Status Quick
                                                 * 快速检查路线图状态，用于检测僵尸状态
                                                 *
                                                 * Args:
                                                 * roadmap_id: 路线图 ID
                                                 * db: 数据库会话
                                                 * service: 状态服务
                                                 *
                                                 * Returns:
                                                 * 包含活跃任务和僵尸概念信息的详细状态
                                                 *
                                                 * Raises:
                                                 * NotFoundError: 路线图不存在
                                                 * @returns ResponseSchemaModel_RoadmapStatusQuickResponse_ Successful Response
                                                 * @throws ApiError
                                                 */
                                                public static checkRoadmapStatusQuickApiV1RoadmapsRoadmapIdStatusQuickGet({
                                                    roadmapId,
                                                }: {
                                                    roadmapId: string,
                                                }): CancelablePromise<ResponseSchemaModel_RoadmapStatusQuickResponse_> {
                                                    return __request(OpenAPI, {
                                                        method: 'GET',
                                                        url: '/api/v1/roadmaps/{roadmap_id}/status/quick',
                                                        path: {
                                                            'roadmap_id': roadmapId,
                                                        },
                                                        errors: {
                                                            422: `Validation Error`,
                                                        },
                                                    });
                                                }
                                                /**
                                                 * Restore Roadmap
                                                 * 从回收站恢复路线图
                                                 *
                                                 * 将软删除的路线图恢复到正常状态。
                                                 *
                                                 * Args:
                                                 * roadmap_id: 路线图 ID
                                                 * db: 数据库会话（自动commit/rollback）
                                                 * current_user: 当前用户（从JWT获取）
                                                 * service: 管理服务
                                                 *
                                                 * Returns:
                                                 * 恢复结果
                                                 *
                                                 * Raises:
                                                 * NotFoundError: 路线图不存在或未被删除
                                                 * ForbiddenError: 无权限恢复此路线图
                                                 * InternalServerError: 恢复失败
                                                 * @returns ResponseSchemaModel_RoadmapRestoreResponse_ Successful Response
                                                 * @throws ApiError
                                                 */
                                                public static restoreRoadmapApiV1RoadmapsRoadmapIdRestorePost({
                                                    roadmapId,
                                                }: {
                                                    roadmapId: string,
                                                }): CancelablePromise<ResponseSchemaModel_RoadmapRestoreResponse_> {
                                                    return __request(OpenAPI, {
                                                        method: 'POST',
                                                        url: '/api/v1/roadmaps/{roadmap_id}/restore',
                                                        path: {
                                                            'roadmap_id': roadmapId,
                                                        },
                                                        errors: {
                                                            422: `Validation Error`,
                                                        },
                                                    });
                                                }
                                                /**
                                                 * Permanently Delete Roadmap
                                                 * 永久删除路线图（不可恢复）
                                                 *
                                                 * ⚠️ 警告：此操作会永久删除所有相关数据，包括：
                                                 * - 路线图元数据
                                                 * - 所有概念(Concept)
                                                 * - 教程(Tutorial)
                                                 * - 资源推荐(Resource)
                                                 * - 测验(Quiz)
                                                 * - 学习进度
                                                 *
                                                 * Args:
                                                 * roadmap_id: 路线图 ID
                                                 * db: 数据库会话（自动commit/rollback）
                                                 * current_user: 当前用户（从JWT获取）
                                                 * service: 管理服务
                                                 *
                                                 * Returns:
                                                 * 删除结果
                                                 *
                                                 * Raises:
                                                 * NotFoundError: 路线图不存在
                                                 * ForbiddenError: 无权限删除此路线图
                                                 * InternalServerError: 删除失败
                                                 * @returns ResponseSchemaModel_RoadmapPermanentDeleteResponse_ Successful Response
                                                 * @throws ApiError
                                                 */
                                                public static permanentlyDeleteRoadmapApiV1RoadmapsRoadmapIdPermanentDelete({
                                                    roadmapId,
                                                }: {
                                                    roadmapId: string,
                                                }): CancelablePromise<ResponseSchemaModel_RoadmapPermanentDeleteResponse_> {
                                                    return __request(OpenAPI, {
                                                        method: 'DELETE',
                                                        url: '/api/v1/roadmaps/{roadmap_id}/permanent',
                                                        path: {
                                                            'roadmap_id': roadmapId,
                                                        },
                                                        errors: {
                                                            422: `Validation Error`,
                                                        },
                                                    });
                                                }
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
                                                                /**
                                                                 * Generate Stream
                                                                 * 流式生成学习路线图（带反压机制）
                                                                 *
                                                                 * 使用 Server-Sent Events (SSE) 实时推送生成过程。
                                                                 *
                                                                 * 性能优化：
                                                                 * - 反压机制：检测客户端断开，立即停止生成，防止资源浪费
                                                                 *
                                                                 * Args:
                                                                 * http_request: FastAPI Request对象（用于检测客户端断开）
                                                                 * request: 用户请求
                                                                 * include_tutorials: 是否包含教程生成阶段（默认 False）
                                                                 *
                                                                 * Returns:
                                                                 * Server-Sent Events 流
                                                                 *
                                                                 * Event 格式：
                                                                 * 需求分析和框架设计阶段：
                                                                 * - chunk: {"type": "chunk", "content": "...", "agent": "..."}
                                                                 * - complete: {"type": "complete", "data": {...}, "agent": "..."}
                                                                 *
                                                                 * 教程生成阶段（当 include_tutorials=True）：
                                                                 * - tutorials_start: {"type": "tutorials_start", "total_count": N}
                                                                 * - batch_start: {"type": "batch_start", "batch_index": 1, ...}
                                                                 * - tutorial_start: {"type": "tutorial_start", "concept_id": "..."}
                                                                 * - tutorial_chunk: {"type": "tutorial_chunk", "concept_id": "..."}
                                                                 * - tutorial_complete: {"type": "tutorial_complete", "concept_id": "..."}
                                                                 * - tutorial_error: {"type": "tutorial_error", "concept_id": "..."}
                                                                 * - batch_complete: {"type": "batch_complete", "batch_index": 1, ...}
                                                                 * - tutorials_done: {"type": "tutorials_done", "summary": {...}}
                                                                 *
                                                                 * 完成：
                                                                 * - done: {"type": "done", "summary": {...}}
                                                                 * - error: {"type": "error", "message": "..."}
                                                                 * @returns any Successful Response
                                                                 * @throws ApiError
                                                                 */
                                                                public static generateStreamApiV1RoadmapsGenerateStreamPost({
                                                                    requestBody,
                                                                    includeTutorials = false,
                                                                }: {
                                                                    requestBody: UserRequest,
                                                                    includeTutorials?: boolean,
                                                                }): CancelablePromise<any> {
                                                                    return __request(OpenAPI, {
                                                                        method: 'POST',
                                                                        url: '/api/v1/roadmaps/generate-stream',
                                                                        query: {
                                                                            'include_tutorials': includeTutorials,
                                                                        },
                                                                        body: requestBody,
                                                                        mediaType: 'application/json',
                                                                        errors: {
                                                                            422: `Validation Error`,
                                                                        },
                                                                    });
                                                                }
                                                                /**
                                                                 * Generate Full Stream
                                                                 * 完整流式生成学习路线图（包含教程生成，带反压机制）
                                                                 *
                                                                 * 这是 /generate-stream?include_tutorials=true 的便捷端点。
                                                                 * 使用 Server-Sent Events (SSE) 实时推送整个生成过程。
                                                                 *
                                                                 * 流程：需求分析 → 框架设计 → 批次教程生成 → 保存数据库
                                                                 *
                                                                 * 性能优化：
                                                                 * - 反压机制：检测客户端断开，立即停止生成，防止LLM Token浪费
                                                                 *
                                                                 * Args:
                                                                 * http_request: FastAPI Request对象（用于检测客户端断开）
                                                                 * request: 用户请求
                                                                 *
                                                                 * Returns:
                                                                 * Server-Sent Events 流（包含所有阶段）
                                                                 * @returns any Successful Response
                                                                 * @throws ApiError
                                                                 */
                                                                public static generateFullStreamApiV1RoadmapsGenerateFullStreamPost({
                                                                    requestBody,
                                                                }: {
                                                                    requestBody: UserRequest,
                                                                }): CancelablePromise<any> {
                                                                    return __request(OpenAPI, {
                                                                        method: 'POST',
                                                                        url: '/api/v1/roadmaps/generate-full-stream',
                                                                        body: requestBody,
                                                                        mediaType: 'application/json',
                                                                        errors: {
                                                                            422: `Validation Error`,
                                                                        },
                                                                    });
                                                                }
                                                                /**
                                                                 * Chat Stream
                                                                 * 聊天式修改入口（流式返回，带反压机制）
                                                                 *
                                                                 * 分析用户自然语言修改意见 → 执行修改 → 流式返回结果
                                                                 *
                                                                 * 性能优化：
                                                                 * - 反压机制：检测客户端断开，立即停止生成
                                                                 *
                                                                 * Args:
                                                                 * http_request: FastAPI Request对象（用于检测客户端断开）
                                                                 * roadmap_id: 路线图 ID
                                                                 * request: 聊天修改请求（包含用户消息、上下文、偏好）
                                                                 *
                                                                 * Returns:
                                                                 * Server-Sent Events 流
                                                                 *
                                                                 * Event 类型：
                                                                 * - analyzing: 正在分析意图
                                                                 * - intents: 检测到的修改意图列表
                                                                 * - modifying: 正在执行某项修改
                                                                 * - agent_progress: Agent 执行进度
                                                                 * - result: 单个修改完成
                                                                 * - done: 全部完成 + 汇总
                                                                 * - error: 错误信息
                                                                 * @returns any Successful Response
                                                                 * @throws ApiError
                                                                 */
                                                                public static chatStreamApiV1RoadmapsRoadmapIdChatStreamPost({
                                                                    roadmapId,
                                                                    requestBody,
                                                                }: {
                                                                    roadmapId: string,
                                                                    requestBody: ChatModificationRequest,
                                                                }): CancelablePromise<any> {
                                                                    return __request(OpenAPI, {
                                                                        method: 'POST',
                                                                        url: '/api/v1/roadmaps/{roadmap_id}/chat-stream',
                                                                        path: {
                                                                            'roadmap_id': roadmapId,
                                                                        },
                                                                        body: requestBody,
                                                                        mediaType: 'application/json',
                                                                        errors: {
                                                                            422: `Validation Error`,
                                                                        },
                                                                    });
                                                                }
                                                                /**
                                                                 * Get Roadmap Cover Image
                                                                 * 获取路线图封面图信息（公开接口，无需认证）
                                                                 *
                                                                 * Args:
                                                                 * roadmap_id: 路线图ID
                                                                 * db: 数据库会话
                                                                 *
                                                                 * Returns:
                                                                 * 封面图信息
                                                                 * @returns CoverImageResponse Successful Response
                                                                 * @throws ApiError
                                                                 */
                                                                public static getRoadmapCoverImageApiV1RoadmapsRoadmapIdCoverImageGet({
                                                                    roadmapId,
                                                                }: {
                                                                    roadmapId: string,
                                                                }): CancelablePromise<CoverImageResponse> {
                                                                    return __request(OpenAPI, {
                                                                        method: 'GET',
                                                                        url: '/api/v1/roadmaps/{roadmap_id}/cover-image',
                                                                        path: {
                                                                            'roadmap_id': roadmapId,
                                                                        },
                                                                        errors: {
                                                                            422: `Validation Error`,
                                                                        },
                                                                    });
                                                                }
                                                                /**
                                                                 * Generate Roadmap Cover Image
                                                                 * 触发路线图封面图生成（异步 Celery 任务）
                                                                 *
                                                                 * ✅ 架构变更：
                                                                 * - 移除 BackgroundTasks（避免 Session 泄漏）
                                                                 * - 改用 Celery 异步任务（独立进程）
                                                                 *
                                                                 * Args:
                                                                 * roadmap_id: 路线图ID
                                                                 * prompt: 可选的图片生成提示词
                                                                 * db: 数据库会话
                                                                 * current_user: 当前用户
                                                                 *
                                                                 * Returns:
                                                                 * 封面图生成状态
                                                                 * @returns CoverImageResponse Successful Response
                                                                 * @throws ApiError
                                                                 */
                                                                public static generateRoadmapCoverImageApiV1RoadmapsRoadmapIdCoverImageGeneratePost({
                                                                    roadmapId,
                                                                    prompt,
                                                                }: {
                                                                    roadmapId: string,
                                                                    prompt?: (string | null),
                                                                }): CancelablePromise<CoverImageResponse> {
                                                                    return __request(OpenAPI, {
                                                                        method: 'POST',
                                                                        url: '/api/v1/roadmaps/{roadmap_id}/cover-image/generate',
                                                                        path: {
                                                                            'roadmap_id': roadmapId,
                                                                        },
                                                                        query: {
                                                                            'prompt': prompt,
                                                                        },
                                                                        errors: {
                                                                            422: `Validation Error`,
                                                                        },
                                                                    });
                                                                }
                                                                /**
                                                                 * Batch Generate Cover Images
                                                                 * 批量生成封面图（异步 Celery 任务）
                                                                 *
                                                                 * 仅触发 pending/failed 状态的封面图生成，跳过已成功生成的。
                                                                 *
                                                                 * ✅ 架构变更：
                                                                 * - 移除 BackgroundTasks（避免 Session 泄漏）
                                                                 * - 改用 Celery 批量任务
                                                                 *
                                                                 * Args:
                                                                 * request: 包含路线图ID列表的请求
                                                                 * db: 数据库会话
                                                                 * current_user: 当前用户
                                                                 *
                                                                 * Returns:
                                                                 * 批量生成状态，包含触发数量和跳过数量
                                                                 * @returns any Successful Response
                                                                 * @throws ApiError
                                                                 */
                                                                public static batchGenerateCoverImagesApiV1RoadmapsCoverImagesBatchGeneratePost({
                                                                    requestBody,
                                                                }: {
                                                                    requestBody: BatchGenerateRequest,
                                                                }): CancelablePromise<any> {
                                                                    return __request(OpenAPI, {
                                                                        method: 'POST',
                                                                        url: '/api/v1/roadmaps/cover-images/batch-generate',
                                                                        body: requestBody,
                                                                        mediaType: 'application/json',
                                                                        errors: {
                                                                            422: `Validation Error`,
                                                                        },
                                                                    });
                                                                }
                                                                /**
                                                                 * Batch Get Cover Images
                                                                 * 批量获取路线图封面图信息（公开接口，无需认证）
                                                                 *
                                                                 * Args:
                                                                 * request: 包含路线图ID列表的请求
                                                                 * db: 数据库会话
                                                                 *
                                                                 * Returns:
                                                                 * 封面图信息列表
                                                                 * @returns BatchCoverImageResponse Successful Response
                                                                 * @throws ApiError
                                                                 */
                                                                public static batchGetCoverImagesApiV1RoadmapsCoverImagesBatchGetPost({
                                                                    requestBody,
                                                                }: {
                                                                    requestBody: BatchGetCoverImagesRequest,
                                                                }): CancelablePromise<Array<BatchCoverImageResponse>> {
                                                                    return __request(OpenAPI, {
                                                                        method: 'POST',
                                                                        url: '/api/v1/roadmaps/cover-images/batch-get',
                                                                        body: requestBody,
                                                                        mediaType: 'application/json',
                                                                        errors: {
                                                                            422: `Validation Error`,
                                                                        },
                                                                    });
                                                                }
                                                            }
