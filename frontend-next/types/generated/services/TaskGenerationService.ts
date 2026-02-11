/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ResponseSchemaModel_CancelTaskResponse_ } from '../models/ResponseSchemaModel_CancelTaskResponse_';
import type { ResponseSchemaModel_GenerateRoadmapResponse_ } from '../models/ResponseSchemaModel_GenerateRoadmapResponse_';
import type { UserRequest } from '../models/UserRequest';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TaskGenerationService {
    /**
     * Generate Roadmap Async
     * 生成学习路线图（Celery 异步任务）
     *
     * 将任务分发到 Celery Worker 执行，FastAPI 进程立即返回。
     *
     * Args:
     * request: 用户请求，包含学习目标和偏好
     * generation_service: 生成服务
     *
     * Returns:
     * 任务 ID，roadmap_id将在需求分析完成后通过WebSocket发送给前端
     *
     * Raises:
     * RequestError: 请求参数错误或任务创建失败
     * InternalServerError: 服务器内部错误
     *
     * Example:
     * ```json
     * {
         * "code": 200,
         * "msg": "Success",
         * "data": {
             * "task_id": "550e8400-e29b-41d4-a716-446655440000",
             * "status": "pending",
             * "message": "路线图生成任务已创建"
             * }
             * }
             * ```
             * @returns ResponseSchemaModel_GenerateRoadmapResponse_ Successful Response
             * @throws ApiError
             */
            public static generateRoadmapAsyncApiV1TasksGeneratePost({
                requestBody,
            }: {
                requestBody: UserRequest,
            }): CancelablePromise<ResponseSchemaModel_GenerateRoadmapResponse_> {
                return __request(OpenAPI, {
                    method: 'POST',
                    url: '/api/v1/tasks/generate',
                    body: requestBody,
                    mediaType: 'application/json',
                    errors: {
                        422: `Validation Error`,
                    },
                });
            }
            /**
             * Cancel Task
             * 取消路线图生成任务
             *
             * 支持取消正在运行的路线图生成任务。取消后，任务状态将变为 "cancelled"，
             * 用户可以稍后重新生成路线图（会从断点继续）。
             *
             * 流程：
             * 1. 验证任务存在且属于当前用户
             * 2. 检查任务状态（仅支持取消 processing 状态）
             * 3. 如果有 celery_task_id，调用 Celery revoke 终止后台任务
             * 4. 更新数据库状态为 "cancelled"
             * 5. 发送 WebSocket 通知
             *
             * Args:
             * task_id: 任务 ID
             * current_user: 当前登录用户
             * generation_service: 生成服务
             *
             * Returns:
             * 取消结果
             *
             * Raises:
             * NotFoundError: 任务不存在
             * ForbiddenError: 无权限取消此任务
             * RequestError: 任务状态不允许取消
             * InternalServerError: 取消失败
             *
             * Example:
             * ```json
             * {
                 * "code": 200,
                 * "msg": "Success",
                 * "data": {
                     * "success": true,
                     * "task_id": "550e8400-e29b-41d4-a716-446655440000",
                     * "message": "任务已取消",
                     * "previous_status": "processing"
                     * }
                     * }
                     * ```
                     * @returns ResponseSchemaModel_CancelTaskResponse_ Successful Response
                     * @throws ApiError
                     */
                    public static cancelTaskApiV1TasksTaskIdCancelPost({
                        taskId,
                    }: {
                        taskId: string,
                    }): CancelablePromise<ResponseSchemaModel_CancelTaskResponse_> {
                        return __request(OpenAPI, {
                            method: 'POST',
                            url: '/api/v1/tasks/{task_id}/cancel',
                            path: {
                                'task_id': taskId,
                            },
                            errors: {
                                422: `Validation Error`,
                            },
                        });
                    }
                }
