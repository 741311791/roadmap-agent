"""
Mentor 模型注册表管理 API
"""
from fastapi import APIRouter, Depends
import structlog

from app.api.v1.deps import CurrentSession, CurrentSessionTransaction
from app.core.auth.deps import current_superuser
from app.core.response_schema import ResponseSchemaModel, response_base
from app.models.database import User
from app.schemas.mentor_model import (
    MentorModelAdminItem,
    MentorModelAdminListResponse,
    MentorModelCreateRequest,
    MentorModelDeleteResponse,
    MentorModelDraftTestRequest,
    MentorModelTestResponse,
    MentorModelUpdateRequest,
)
from app.services.shared.mentor_model_registry_service import (
    MentorModelRegistryService,
    get_mentor_model_registry_service,
)

router = APIRouter(prefix="/mentor-models", tags=["admin-mentor-models"])
logger = structlog.get_logger()


@router.get("", response_model=ResponseSchemaModel[MentorModelAdminListResponse])
async def list_mentor_models(
    db: CurrentSession,
    current_user: User = Depends(current_superuser),
    service: MentorModelRegistryService = Depends(get_mentor_model_registry_service),
) -> ResponseSchemaModel[MentorModelAdminListResponse]:
    """
    获取 Mentor 模型注册表列表
    """
    items = await service.list_admin_models(db)
    logger.info(
        "admin_list_mentor_models",
        admin_id=current_user.id,
        total=len(items),
    )
    return response_base.success(
        data=MentorModelAdminListResponse(
            items=items,
            total=len(items),
        )
    )


@router.post("", response_model=ResponseSchemaModel[MentorModelAdminItem])
async def create_mentor_model(
    request: MentorModelCreateRequest,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
    service: MentorModelRegistryService = Depends(get_mentor_model_registry_service),
) -> ResponseSchemaModel[MentorModelAdminItem]:
    """
    创建 Mentor 模型配置
    """
    created_record = await service.create_model(db, request)
    logger.info(
        "admin_create_mentor_model",
        admin_id=current_user.id,
        model_id=created_record.model_id,
        model_name=created_record.model_name,
    )
    admin_items = await service.list_admin_models(db)
    created_item = next(
        item for item in admin_items if item.model_id == created_record.model_id
    )
    return response_base.success(data=created_item)


@router.patch("/{model_id}", response_model=ResponseSchemaModel[MentorModelAdminItem])
async def update_mentor_model(
    model_id: str,
    request: MentorModelUpdateRequest,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
    service: MentorModelRegistryService = Depends(get_mentor_model_registry_service),
) -> ResponseSchemaModel[MentorModelAdminItem]:
    """
    更新 Mentor 模型配置
    """
    updated_record = await service.update_model(
        db,
        model_id=model_id,
        request=request,
    )
    logger.info(
        "admin_update_mentor_model",
        admin_id=current_user.id,
        model_id=updated_record.model_id,
    )
    admin_items = await service.list_admin_models(db)
    updated_item = next(
        item for item in admin_items if item.model_id == updated_record.model_id
    )
    return response_base.success(data=updated_item)


@router.delete("/{model_id}", response_model=ResponseSchemaModel[MentorModelDeleteResponse])
async def delete_mentor_model(
    model_id: str,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
    service: MentorModelRegistryService = Depends(get_mentor_model_registry_service),
) -> ResponseSchemaModel[MentorModelDeleteResponse]:
    """
    删除 Mentor 模型配置
    """
    deleted_record = await service.delete_model(
        db,
        model_id=model_id,
    )
    logger.info(
        "admin_delete_mentor_model",
        admin_id=current_user.id,
        model_id=deleted_record.model_id,
    )
    return response_base.success(
        data=MentorModelDeleteResponse(model_id=deleted_record.model_id)
    )


@router.post("/test", response_model=ResponseSchemaModel[MentorModelTestResponse])
async def test_mentor_model_draft(
    request: MentorModelDraftTestRequest,
    current_user: User = Depends(current_superuser),
    service: MentorModelRegistryService = Depends(get_mentor_model_registry_service),
) -> ResponseSchemaModel[MentorModelTestResponse]:
    """
    测试未保存的 Mentor 模型草稿配置
    """
    test_result = await service.test_draft_model(request)
    logger.info(
        "admin_test_mentor_model_draft",
        admin_id=current_user.id,
        provider=request.provider,
        model_name=request.model_name,
        success=test_result.success,
    )
    return response_base.success(data=test_result)


@router.post("/{model_id}/test", response_model=ResponseSchemaModel[MentorModelTestResponse])
async def test_registered_mentor_model(
    model_id: str,
    db: CurrentSessionTransaction,
    current_user: User = Depends(current_superuser),
    service: MentorModelRegistryService = Depends(get_mentor_model_registry_service),
) -> ResponseSchemaModel[MentorModelTestResponse]:
    """
    测试已保存的 Mentor 模型配置
    """
    test_result = await service.test_registered_model(
        db,
        model_id=model_id,
    )
    logger.info(
        "admin_test_registered_mentor_model",
        admin_id=current_user.id,
        model_id=model_id,
        success=test_result.success,
    )
    return response_base.success(data=test_result)

