/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 泛型响应模型（带类型提示）
 *
 * 使用泛型参数指定data字段的具体类型，提供更好的类型安全性和文档生成。
 *
 * 使用示例：
 * ```python
 * from app.schemas.user import UserDetail
 * from app.core.response_schema import ResponseSchemaModel
 *
 * @router.get("/users/{user_id}", response_model=ResponseSchemaModel[UserDetail])
 * async def get_user(user_id: str) -> ResponseSchemaModel[UserDetail]:
 * user = await user_service.get_user(user_id)
 * return response_base.success(data=user)
 * ```
 */
export type ResponseSchemaModel = {
    /**
     * HTTP状态码
     */
    code: number;
    /**
     * 响应消息（用户友好）
     */
    msg: string;
    data: any;
};

