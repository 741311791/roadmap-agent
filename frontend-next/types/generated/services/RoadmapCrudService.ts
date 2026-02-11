/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ResponseSchemaModel_RoadmapDeleteResponse_ } from '../models/ResponseSchemaModel_RoadmapDeleteResponse_';
import type { ResponseSchemaModel_RoadmapPermanentDeleteResponse_ } from '../models/ResponseSchemaModel_RoadmapPermanentDeleteResponse_';
import type { ResponseSchemaModel_RoadmapRestoreResponse_ } from '../models/ResponseSchemaModel_RoadmapRestoreResponse_';
import type { ResponseSchemaModel_RoadmapStatusQuickResponse_ } from '../models/ResponseSchemaModel_RoadmapStatusQuickResponse_';
import type { ResponseSchemaModel_RoadmapStatusResponse_ } from '../models/ResponseSchemaModel_RoadmapStatusResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class RoadmapCrudService {
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
}
