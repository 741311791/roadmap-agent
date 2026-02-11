/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ConceptStatusResponse } from '../models/ConceptStatusResponse';
import type { GenerateSingleConceptRequest } from '../models/GenerateSingleConceptRequest';
import type { ModifyContentRequest } from '../models/ModifyContentRequest';
import type { ResponseModel } from '../models/ResponseModel';
import type { ResponseSchemaModel_QuizResponse_ } from '../models/ResponseSchemaModel_QuizResponse_';
import type { ResponseSchemaModel_ResourcesResponse_ } from '../models/ResponseSchemaModel_ResourcesResponse_';
import type { ResponseSchemaModel_RetryContentResponse_ } from '../models/ResponseSchemaModel_RetryContentResponse_';
import type { ResponseSchemaModel_TutorialDetailResponse_ } from '../models/ResponseSchemaModel_TutorialDetailResponse_';
import type { ResponseSchemaModel_TutorialVersionListResponse_ } from '../models/ResponseSchemaModel_TutorialVersionListResponse_';
import type { RetryContentRequest } from '../models/RetryContentRequest';
import type { RoadmapConceptsStatusResponse } from '../models/RoadmapConceptsStatusResponse';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ContentManagementService {
    /**
     * 获取 Roadmap 的所有 Concept 状态
     * 获取某 roadmap 的所有 Concept 内容生成状态。
     *
     * **用途**：
     * - 页面刷新后恢复状态显示
     * - 查询内容生成进度
     *
     * **状态说明**：
     * - `pending`: 未开始
     * - `generating`: 生成中
     * - `completed`: 已完成
     * - `partial_failed`: 部分失败（至少一项成功）
     * - `failed`: 全部失败
     * @returns RoadmapConceptsStatusResponse Successful Response
     * @throws ApiError
     */
    public static getRoadmapConceptsStatusApiV1RoadmapsRoadmapIdGet({
        roadmapId,
    }: {
        roadmapId: string,
    }): CancelablePromise<RoadmapConceptsStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
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
     * Get Tutorial Versions
     * 获取指定概念的所有教程版本历史
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * session: 数据库会话
     * service: 内容服务
     *
     * Returns:
     * 教程版本列表（按版本号降序，最新版本在前）
     *
     * Raises:
     * NotFoundError: 概念没有教程
     * @returns ResponseSchemaModel_TutorialVersionListResponse_ Successful Response
     * @throws ApiError
     */
    public static getTutorialVersionsApiV1ContentRoadmapIdConceptsConceptIdTutorialsGet({
        roadmapId,
        conceptId,
    }: {
        roadmapId: string,
        conceptId: string,
    }): CancelablePromise<ResponseSchemaModel_TutorialVersionListResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/tutorials',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Latest Tutorial
     * 获取指定概念的最新教程版本
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * session: 数据库会话
     * service: 内容服务
     *
     * Returns:
     * 最新版本的教程元数据
     *
     * Raises:
     * NotFoundError: 概念没有教程
     * @returns ResponseSchemaModel_TutorialDetailResponse_ Successful Response
     * @throws ApiError
     */
    public static getLatestTutorialApiV1ContentRoadmapIdConceptsConceptIdTutorialsLatestGet({
        roadmapId,
        conceptId,
    }: {
        roadmapId: string,
        conceptId: string,
    }): CancelablePromise<ResponseSchemaModel_TutorialDetailResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/tutorials/latest',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Tutorial By Version
     * 获取指定概念的特定版本教程
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * version: 版本号
     * session: 数据库会话
     * service: 内容服务
     *
     * Returns:
     * 指定版本的教程元数据
     *
     * Raises:
     * NotFoundError: 指定版本的教程不存在
     * @returns ResponseSchemaModel_TutorialDetailResponse_ Successful Response
     * @throws ApiError
     */
    public static getTutorialByVersionApiV1ContentRoadmapIdConceptsConceptIdTutorialsVVersionGet({
        roadmapId,
        conceptId,
        version,
    }: {
        roadmapId: string,
        conceptId: string,
        version: number,
    }): CancelablePromise<ResponseSchemaModel_TutorialDetailResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/tutorials/v{version}',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
                'version': version,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Download Latest Tutorial Content
     * 下载最新版本教程的 Markdown 内容（后端代理）
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * session: 数据库会话
     * service: 内容服务
     *
     * Returns:
     * 教程的 Markdown 文本内容（PlainText格式）
     *
     * Raises:
     * NotFoundError: 教程不存在或未完成
     * InternalServerError: 下载失败
     * @returns string Successful Response
     * @throws ApiError
     */
    public static downloadLatestTutorialContentApiV1ContentRoadmapIdConceptsConceptIdTutorialsLatestContentGet({
        roadmapId,
        conceptId,
    }: {
        roadmapId: string,
        conceptId: string,
    }): CancelablePromise<string> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/tutorials/latest/content',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Concept Resources
     * 获取指定概念的学习资源
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * session: 数据库会话
     * service: 内容服务
     *
     * Returns:
     * 资源推荐列表
     *
     * Raises:
     * NotFoundError: 概念没有资源推荐
     * @returns ResponseSchemaModel_ResourcesResponse_ Successful Response
     * @throws ApiError
     */
    public static getConceptResourcesApiV1ContentRoadmapIdConceptsConceptIdResourcesGet({
        roadmapId,
        conceptId,
    }: {
        roadmapId: string,
        conceptId: string,
    }): CancelablePromise<ResponseSchemaModel_ResourcesResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/resources',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Concept Quiz
     * 获取指定概念的测验
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * session: 数据库会话
     * service: 内容服务
     *
     * Returns:
     * 测验数据，包含题目列表
     *
     * Raises:
     * NotFoundError: 概念没有测验
     * @returns ResponseSchemaModel_QuizResponse_ Successful Response
     * @throws ApiError
     */
    public static getConceptQuizApiV1ContentRoadmapIdConceptsConceptIdQuizGet({
        roadmapId,
        conceptId,
    }: {
        roadmapId: string,
        conceptId: string,
    }): CancelablePromise<ResponseSchemaModel_QuizResponse_> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/quiz',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 重新生成教程
     * 重新生成单个Concept的教程内容。
     *
     * 这是Concept编辑功能的一部分，不属于Retry（checkpoint恢复）功能。
     * 直接调用TutorialGeneratorAgent重新生成，不使用LangGraph checkpoint机制。
     *
     * 适用场景：
     * - 单个教程质量不满意
     * - 需要不同风格的教程
     * - 调整教程详细度
     * @returns ResponseSchemaModel_RetryContentResponse_ Successful Response
     * @throws ApiError
     */
    public static regenerateTutorialApiV1ContentRoadmapIdConceptsConceptIdTutorialRegeneratePost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: RetryContentRequest,
    }): CancelablePromise<ResponseSchemaModel_RetryContentResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/tutorial/regenerate',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 重新生成资源推荐
     * 重新生成单个Concept的资源推荐内容。
     *
     * 这是Concept编辑功能的一部分，不属于Retry功能。
     * @returns ResponseSchemaModel_RetryContentResponse_ Successful Response
     * @throws ApiError
     */
    public static regenerateResourcesApiV1ContentRoadmapIdConceptsConceptIdResourcesRegeneratePost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: RetryContentRequest,
    }): CancelablePromise<ResponseSchemaModel_RetryContentResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/resources/regenerate',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 重新生成测验
     * 重新生成单个Concept的测验内容。
     *
     * 这是Concept编辑功能的一部分，不属于Retry功能。
     * @returns ResponseSchemaModel_RetryContentResponse_ Successful Response
     * @throws ApiError
     */
    public static regenerateQuizApiV1ContentRoadmapIdConceptsConceptIdQuizRegeneratePost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: RetryContentRequest,
    }): CancelablePromise<ResponseSchemaModel_RetryContentResponse_> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/content/{roadmap_id}/concepts/{concept_id}/quiz/regenerate',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Modify Quiz
     * 修改指定概念的测验内容
     *
     * Args:
     * roadmap_id: 路线图 ID
     * concept_id: 概念 ID
     * request: 修改请求
     * session: 数据库会话
     * service: 内容服务
     *
     * Returns:
     * 修改后的测验信息
     *
     * Raises:
     * HTTPException: 404/500 错误
     * @returns any Successful Response
     * @throws ApiError
     */
    public static modifyQuizApiV1RoadmapIdConceptsConceptIdQuizModifyPost({
        roadmapId,
        conceptId,
        requestBody,
    }: {
        roadmapId: string,
        conceptId: string,
        requestBody: ModifyContentRequest,
    }): CancelablePromise<any> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/{roadmap_id}/concepts/{concept_id}/quiz/modify',
            path: {
                'roadmap_id': roadmapId,
                'concept_id': conceptId,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * 获取单个 Concept 状态
     * 获取指定 Concept 的内容生成状态
     * @returns ConceptStatusResponse Successful Response
     * @throws ApiError
     */
    public static getConceptStatusApiV1ConceptsConceptIdGet({
        conceptId,
    }: {
        conceptId: string,
    }): CancelablePromise<ConceptStatusResponse> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/concepts/{concept_id}',
            path: {
                'concept_id': conceptId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Generate Single Concept Content
     * 独立调用单 Concept 子图生成内容（Celery 异步任务）
     *
     * 此接口允许单独重新生成某个 Concept 的内容，不依赖完整的工作流。
     * 任务将分发到 Celery Worker 执行，FastAPI 进程立即返回任务 ID。
     *
     * 架构说明：
     * - ✅ API 层只负责 HTTP 适配和 Celery 任务分发
     * - ✅ 任务在独立的 Worker 进程中执行
     * - ✅ 通过 WebSocket 推送任务进度和结果
     * - ✅ 遵循分层架构设计规范
     *
     * Args:
     * request: 请求参数
     * user: 当前用户
     *
     * Returns:
     * Celery 任务 ID 和任务状态
     *
     * Raises:
     * 500: 任务分发失败
     *
     * 使用流程：
     * 1. 调用此接口获取 celery_task_id
     * 2. 通过 WebSocket 订阅 `roadmap:{roadmap_id}` 频道
     * 3. 接收实时进度通知和最终结果
     * @returns ResponseModel Successful Response
     * @throws ApiError
     */
    public static generateSingleConceptContentApiV1SubgraphGenerateSingleConceptPost({
        requestBody,
    }: {
        requestBody: GenerateSingleConceptRequest,
    }): CancelablePromise<ResponseModel> {
        return __request(OpenAPI, {
            method: 'POST',
            url: '/api/v1/subgraph/generate-single-concept',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                422: `Validation Error`,
            },
        });
    }
    /**
     * Get Task Status
     * 查询 Celery 任务状态
     *
     * Args:
     * celery_task_id: Celery 任务 ID
     *
     * Returns:
     * 任务状态信息
     * @returns ResponseModel Successful Response
     * @throws ApiError
     */
    public static getTaskStatusApiV1SubgraphTaskCeleryTaskIdStatusGet({
        celeryTaskId,
    }: {
        celeryTaskId: string,
    }): CancelablePromise<ResponseModel> {
        return __request(OpenAPI, {
            method: 'GET',
            url: '/api/v1/subgraph/task/{celery_task_id}/status',
            path: {
                'celery_task_id': celeryTaskId,
            },
            errors: {
                422: `Validation Error`,
            },
        });
    }
}
