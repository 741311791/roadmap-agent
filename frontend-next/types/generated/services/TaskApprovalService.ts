/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ApprovalRequest } from '../models/ApprovalRequest';
import type { ResponseSchemaModel_ApprovalResponse_ } from '../models/ResponseSchemaModel_ApprovalResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class TaskApprovalService {
    /**
     * Approve Roadmap
     * 人工审核端点（Human-in-the-Loop）
     *
     * Args:
     * task_id: 任务ID
     * request: 审核请求（包含批准/拒绝和反馈）
     * orchestrator: 工作流执行器
     *
     * Returns:
     * 审核结果
     *
     * Raises:
     * NotFoundError: 任务不存在
     * RequestError: 任务状态不正确
     * InternalServerError: 处理审核结果失败
     * @returns ResponseSchemaModel_ApprovalResponse_ Successful Response
     * @throws ApiError
     */
    public static approveRoadmapApiV1TasksTaskIdApprovePost({
        taskId,
        requestBody,
    }: {
        taskId: string,
        requestBody: ApprovalRequest,
    }): CancelablePromise<ResponseSchemaModel_ApprovalResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/tasks/{task_id}/approve',
            path: {
                'task_id': taskId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
