/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ResponseSchemaModel_QuizResponse_ } from '../models/ResponseSchemaModel_QuizResponse_';
import type { ResponseSchemaModel_ResourcesResponse_ } from '../models/ResponseSchemaModel_ResourcesResponse_';
import type { ResponseSchemaModel_TutorialDetailResponse_ } from '../models/ResponseSchemaModel_TutorialDetailResponse_';
import type { ResponseSchemaModel_TutorialVersionListResponse_ } from '../models/ResponseSchemaModel_TutorialVersionListResponse_';
import type { CancelablePromise } from '../core/CancelablePromise';
import { OpenAPI } from '../core/OpenAPI';
import { request as __request } from '../core/request';
export class ContentQueryService {
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
}
