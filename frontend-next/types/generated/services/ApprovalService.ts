/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ApprovalService {
    /**
     * Approve Roadmap
     * 人工审核端点（Human-in-the-Loop）
     *
     * 在路线图框架生成后，允许用户审核并决定是否继续生成详细内容
     *
     * Args:
     * task_id: 任务 ID
     * approved: 是否批准（True=批准继续生成，False=拒绝需要修改）
     * feedback: 用户反馈（如果未批准，说明需要修改的内容）
     * db: 数据库会话
     * orchestrator: 工作流执行器
     *
     * Returns:
     * 审核处理结果
     *
     * Raises:
     * HTTPException:
     * - 400: 任务状态不正确或参数错误
     * - 500: 处理审核结果时发生错误
     *
     * Example Request:
     * ```json
     * {
         * "approved": true,
         * "feedback": null
         * }
         * ```
         *
         * Example Response (Approved):
         * ```json
         * {
             * "status": "approved",
             * "message": "审核通过，继续生成详细内容",
             * "task_id": "550e8400-e29b-41d4-a716-446655440000"
             * }
             * ```
             *
             * Example Response (Rejected):
             * ```json
             * {
                 * "status": "rejected",
                 * "message": "审核未通过，需要重新设计",
                 * "task_id": "550e8400-e29b-41d4-a716-446655440000",
                 * "feedback": "需要增加更多实战项目"
                 * }
                 * ```
                 * @returns any Successful Response
                 * @throws ApiError
                 */
                public static approveRoadmapApiV1RoadmapsTaskIdApprovePost({
                    taskId,
                    approved,
                    feedback,
                }: {
                    taskId: string,
                    approved: boolean,
                    feedback?: (string | null),
                }): CancelablePromise<any> {
                    return __request(OpenAPI, {
                        method: 'POST',
                        url: '/api/v1/roadmaps/{task_id}/approve',
                        path: {
                            'task_id': taskId,
                        },
                        query: {
                            'approved': approved,
                            'feedback': feedback,
                        },
                        errors: {
                            422: `Validation Error`,
                        },
                    });
                }
            }
