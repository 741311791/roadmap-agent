/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ResponseSchemaModel } from '../models/ResponseSchemaModel';
import type { ResponseSchemaModel_ContentGenerationStatusResponse_ } from '../models/ResponseSchemaModel_ContentGenerationStatusResponse_';
import type { ResponseSchemaModel_Dict_str__Any__ } from '../models/ResponseSchemaModel_Dict_str__Any__';
import type { ResponseSchemaModel_TaskListResponse_ } from '../models/ResponseSchemaModel_TaskListResponse_';
import type { ResponseSchemaModel_TaskStatusDetailResponse_ } from '../models/ResponseSchemaModel_TaskStatusDetailResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TaskQueryService {
    /**
     * Get Generation Status
     * 查询路线图生成任务状态
     *
     * Args:
     * task_id: 任务ID
     * orchestrator: 工作流执行器
     *
     * Returns:
     * 任务状态信息
     *
     * Raises:
     * NotFoundError: 任务不存在
     * @returns ResponseSchemaModel_TaskStatusDetailResponse_ Successful Response
     * @throws ApiError
     */
    public static getGenerationStatusApiV1TasksTaskIdStatusGet({
        taskId,
    }: {
        taskId: string,
    }): CancelablePromise<ResponseSchemaModel_TaskStatusDetailResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/tasks/{task_id}/status',
            path: {
                'task_id': taskId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Content Generation Status
     * 查询内容生成进度（Celery 任务状态）
     *
     * 当路线图框架生成完成后，内容生成（教程、资源、测验）会在独立的 Celery Worker 中执行。
     * 该接口用于查询内容生成的实时进度。
     *
     * Args:
     * task_id: 任务 ID
     *
     * Returns:
     * 内容生成状态信息
     *
     * Raises:
     * NotFoundError: 任务不存在
     *
     * Example:
     * ```json
     * {
         * "code": 200,
         * "msg": "Success",
         * "data": {
             * "task_id": "550e8400-e29b-41d4-a716-446655440000",
             * "celery_task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
             * "status": "PROGRESS",
             * "progress": {
                 * "current": 15,
                 * "total": 30,
                 * "percentage": 50.0
                 * },
                 * "result": null
                 * }
                 * }
                 * ```
                 * @returns ResponseSchemaModel_ContentGenerationStatusResponse_ Successful Response
                 * @throws ApiError
                 */
                public static getContentGenerationStatusApiV1TasksTaskIdContentStatusGet({
                    taskId,
                }: {
                    taskId: string,
                }): CancelablePromise<ResponseSchemaModel_ContentGenerationStatusResponse_> {
                    return __request(OpenAPI, {
                        method: 'GET',
                        url: '/api/v1/tasks/{task_id}/content-status',
                        path: {
                            'task_id': taskId,
                        },
                        errors: {
                            422: `Validation Error`,
                        },
                    });
                }
                /**
                 * Get User Tasks
                 * 获取当前用户的任务列表，支持按状态和任务类型筛选
                 *
                 * Args:
                 * db: 数据库会话
                 * current_user: 当前用户（从JWT提取）
                 * service: 用户服务
                 * status: 任务状态筛选（可选）：pending, processing, completed, failed
                 * task_type: 任务类型筛选（可选）：creation, retry_tutorial, retry_resources, retry_quiz, retry_batch
                 * limit: 返回数量限制（默认50）
                 * offset: 分页偏移（默认0）
                 *
                 * Returns:
                 * 任务列表及各状态统计
                 *
                 * 状态归类说明：
                 * - pending: 仅 pending
                 * - processing: processing, running, human_review_pending, human_review_required
                 * - completed: completed, partial_failure, approved
                 * - failed: failed, rejected
                 *
                 * Example:
                 * ```json
                 * {
                     * "code": 200,
                     * "msg": "Success",
                     * "data": {
                         * "tasks": [
                             * {
                                 * "task_id": "550e8400-e29b-41d4-a716-446655440000",
                                 * "status": "human_review_pending",
                                 * "current_step": "human_review",
                                 * "title": "Python Web Development",
                                 * "created_at": "2024-01-01T00:00:00Z",
                                 * "updated_at": "2024-01-01T00:01:00Z",
                                 * "completed_at": null,
                                 * "error_message": null,
                                 * "roadmap_id": "python-guide-xxx"
                                 * }
                                 * ],
                                 * "total": 1,
                                 * "pending_count": 0,
                                 * "processing_count": 1,
                                 * "completed_count": 5,
                                 * "failed_count": 0
                                 * }
                                 * }
                                 * ```
                                 * @returns ResponseSchemaModel_TaskListResponse_ Successful Response
                                 * @throws ApiError
                                 */
                                public static getUserTasksApiV1TasksMyGet({
                                    status,
                                    taskType,
                                    limit = 50,
                                    offset,
                                }: {
                                    status?: (string | null),
                                    taskType?: (string | null),
                                    limit?: number,
                                    offset?: number,
                                }): CancelablePromise<ResponseSchemaModel_TaskListResponse_> {
                                    return __request(OpenAPI, {
                                        method: 'GET',
                                        url: '/api/v1/tasks/my',
                                        query: {
                                            'status': status,
                                            'task_type': taskType,
                                            'limit': limit,
                                            'offset': offset,
                                        },
                                        errors: {
                                            422: `Validation Error`,
                                        },
                                    });
                                }
                                /**
                                 * Get Active Task
                                 * 获取路线图当前的活跃任务
                                 *
                                 * Args:
                                 * roadmap_id: 路线图 ID
                                 * db: 数据库会话
                                 * service: 状态服务
                                 *
                                 * Returns:
                                 * 活跃任务信息
                                 * @returns ResponseSchemaModel_Dict_str__Any__ Successful Response
                                 * @throws ApiError
                                 */
                                public static getActiveTaskApiV1TasksRoadmapsRoadmapIdActiveTaskGet({
                                    roadmapId,
                                }: {
                                    roadmapId: string,
                                }): CancelablePromise<ResponseSchemaModel_Dict_str__Any__> {
                                    return __request(OpenAPI, {
                                        method: 'GET',
                                        url: '/api/v1/tasks/roadmaps/{roadmap_id}/active-task',
                                        path: {
                                            'roadmap_id': roadmapId,
                                        },
                                        errors: {
                                            422: `Validation Error`,
                                        },
                                    });
                                }
                                /**
                                 * Get Active Retry Task
                                 * 获取路线图当前正在进行的重试任务
                                 *
                                 * Args:
                                 * roadmap_id: 路线图 ID
                                 * db: 数据库会话
                                 * service: 状态服务
                                 *
                                 * Returns:
                                 * 重试任务信息
                                 *
                                 * Raises:
                                 * NotFoundError: 路线图不存在
                                 * @returns ResponseSchemaModel_Dict_str__Any__ Successful Response
                                 * @throws ApiError
                                 */
                                public static getActiveRetryTaskApiV1TasksRoadmapsRoadmapIdActiveRetryTaskGet({
                                    roadmapId,
                                }: {
                                    roadmapId: string,
                                }): CancelablePromise<ResponseSchemaModel_Dict_str__Any__> {
                                    return __request(OpenAPI, {
                                        method: 'GET',
                                        url: '/api/v1/tasks/roadmaps/{roadmap_id}/active-retry-task',
                                        path: {
                                            'roadmap_id': roadmapId,
                                        },
                                        errors: {
                                            422: `Validation Error`,
                                        },
                                    });
                                }
                                /**
                                 * Get Task Edit History Full
                                 * 获取任务关联路线图的完整编辑历史（包含详细diff和修改内容）
                                 *
                                 * 这是一个便捷端点，根据 task_id 查找关联的 roadmap_id，然后返回编辑历史。
                                 *
                                 * Args:
                                 * task_id: 任务ID
                                 * db: 数据库会话
                                 *
                                 * Returns:
                                 * 完整编辑历史列表（按时间倒序）
                                 *
                                 * Raises:
                                 * NotFoundError: 任务不存在或任务未关联路线图
                                 *
                                 * Example:
                                 * ```json
                                 * {
                                     * "code": 200,
                                     * "msg": "Success",
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
                                                 * ```
                                                 * @returns ResponseSchemaModel Successful Response
                                                 * @throws ApiError
                                                 */
                                                public static getTaskEditHistoryFullApiV1TasksTaskIdEditHistoryFullGet({
                                                    taskId,
                                                }: {
                                                    taskId: string,
                                                }): CancelablePromise<ResponseSchemaModel> {
                                                    return __request(OpenAPI, {
                                                        method: 'GET',
                                                        url: '/api/v1/tasks/{task_id}/edit/history-full',
                                                        path: {
                                                            'task_id': taskId,
                                                        },
                                                        errors: {
                                                            422: `Validation Error`,
                                                        },
                                                    });
                                                }
                                            }
