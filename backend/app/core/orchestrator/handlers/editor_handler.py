"""
编辑Handler

处理EditorNode的输出保存
"""
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from .base import NodeOutputHandler
from app.crud.crud_edit import get_edit_crud
from app.crud.crud_roadmap import get_roadmap_crud
from app.schemas.handler_io import EditorHandlerInput

logger = structlog.get_logger()


class EditorHandler(NodeOutputHandler[EditorHandlerInput]):
    """
    编辑Handler
    
    职责：
    1. 保存路线图编辑记录
    2. 更新路线图框架
    """
    
    input_model_class = EditorHandlerInput
    
    def get_node_name(self) -> str:
        return "roadmap_edit"
    
    async def _handle_output(
        self,
        output: EditorHandlerInput,
        task_id: str,
        session: AsyncSession,
    ) -> None:
        """
        处理编辑输出（具体实现）
        
        Args:
            output: 编辑 Handler 输入（强类型）
            task_id: 任务ID
            session: 数据库会话
        """
        modified_framework = output.modified_framework
        origin_framework = output.origin_framework
        roadmap_id = output.roadmap_id
        user_id = output.user_id
        edit_round = output.edit_round
        
        logger.info(
            "editor_handler_saving",
            task_id=task_id,
            roadmap_id=roadmap_id,
            edit_round=edit_round,
        )
        
        # 计算修改的节点ID
        modified_node_ids = self._compute_modified_node_ids(
            origin_framework,
            modified_framework,
        )
        
        # 创建编辑记录
        edit_crud = get_edit_crud()
        await edit_crud.create_edit_record(
            session=session,
            task_id=task_id,
            roadmap_id=roadmap_id,
            origin_framework_data=origin_framework.model_dump() if origin_framework else {},
            modified_framework_data=modified_framework.model_dump(),
            modification_summary=f"AI 根据第 {edit_round} 轮反馈优化了路线图结构",
            modified_node_ids=modified_node_ids,
            edit_round=edit_round,
        )
        
        # 更新路线图框架
        roadmap_crud = get_roadmap_crud()
        await roadmap_crud.save_roadmap_metadata(
            session,
            roadmap_id,
            user_id,
            modified_framework,
        )
        
        logger.info(
            "editor_handler_saved",
            task_id=task_id,
            roadmap_id=roadmap_id,
            edit_round=edit_round,
            modified_nodes_count=len(modified_node_ids),
        )
    
    def _compute_modified_node_ids(
        self,
        origin_framework,
        modified_framework,
    ) -> list[str]:
        """
        计算修改过的节点ID
        
        Args:
            origin_framework: 原始框架
            modified_framework: 修改后的框架
        
        Returns:
            修改过的concept_id列表
        """
        from app.services.roadmaps.roadmap_comparison_service import (
            RoadmapComparisonService
        )
        
        if not origin_framework:
            # 如果没有原始框架，返回所有节点
            modified_ids = []
            for stage in modified_framework.stages:
                for module in stage.modules:
                    modified_ids.extend([c.concept_id for c in module.concepts])
            return modified_ids
        
        # 使用通用比对服务
        comparison_service = RoadmapComparisonService()
        modified_ids = comparison_service.get_modified_node_ids_simple(
            origin_framework,
            modified_framework,
        )
        
        logger.debug(
            "compute_modified_node_ids",
            changed_count=len(modified_ids),
        )
        
        return modified_ids

