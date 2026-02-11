"""
内容生成节点（纯函数）

职责：
- 调用内容生成子图
- 返回纯数据（不保存数据库）
"""
import structlog
from langchain_core.runnables import RunnableConfig

from app.core.orchestrator.base import RoadmapState
from app.core.orchestrator.runtime_context import RuntimeContext
from app.core.orchestrator.subgraphs.content_generation import build_content_generation_subgraph

logger = structlog.get_logger()


def extract_concepts_from_framework(framework) -> list:
    """
    从路线图框架中提取所有Concept
    
    Args:
        framework: RoadmapFramework对象
    
    Returns:
        Concept列表
    """
    concepts = []
    for stage in framework.stages:
        for module in stage.modules:
            concepts.extend(module.concepts)
    return concepts


async def content_generation_node(
    state: RoadmapState,
    config: RunnableConfig,
) -> dict:
    """
    内容生成节点（双 Checkpointer 架构 - V3）
    
    调用内容生成子图（两层 Fan-Out/Fan-In 架构）。
    子图内部会：
    1. 为每个 Concept 创建子图实例
    2. 每个子图并发生成 Tutorial、Resource、Quiz
    3. Fan-In 收集并保存元数据
    4. 最终汇总并批量更新 Framework
    
    双 Checkpointer 架构：
    1. 主图 checkpointer 记录："我正在执行 content_generation 节点"
    2. 子图 checkpointer 记录："我在并发执行哪些 Concept，哪些已完成"
    3. 共享 thread_id（task_id），实现逻辑关联
    4. LangGraph 自动跳过已完成的节点，只重试失败的部分
    
    Args:
        state: 工作流状态
        config: 运行时配置（包含RuntimeContext和thread_id）
    
    Returns:
        状态更新字典：
        - concept_results: 所有 Concept 的结果列表
        - current_step: 当前步骤
    """
    # 从config获取依赖
    ctx: RuntimeContext = config["configurable"]["runtime_context"]
    
    task_id = state["task_id"]
    roadmap_id = state.get("roadmap_id")
    framework = state.get("roadmap_framework")
    user_request = state["user_request"]
    
    if not framework:
        raise ValueError("路线图框架不存在，无法生成内容")
    
    if not roadmap_id:
        raise ValueError("roadmap_id 不存在，无法生成内容")
    
    # ============ 测试模式：截断 Framework（只保留第一个Stage的第一个Module） ============
    # 从环境变量获取配置
    from app.config.settings import settings
    
    if settings.TEST_MODE_TRUNCATE_FRAMEWORK:
        logger.warning(
            "test_mode_truncate_framework_enabled",
            task_id=task_id,
            original_stages=len(framework.stages),
            original_modules=sum(len(stage.modules) for stage in framework.stages),
            original_concepts=sum(
                len(module.concepts)
                for stage in framework.stages
                for module in stage.modules
            ),
        )
        
        # 深拷贝framework以避免修改原始对象
        from copy import deepcopy
        framework = deepcopy(framework)
        
        # 只保留第一个Stage
        if framework.stages:
            first_stage = framework.stages[0]
            # 只保留第一个Module
            if first_stage.modules:
                first_module = first_stage.modules[0]
                first_stage.modules = [first_module]
            framework.stages = [first_stage]
        
        logger.info(
            "test_mode_framework_truncated",
            task_id=task_id,
            truncated_stages=len(framework.stages),
            truncated_modules=sum(len(stage.modules) for stage in framework.stages),
            truncated_concepts=sum(
                len(module.concepts)
                for stage in framework.stages
                for module in stage.modules
            ),
        )
    
    # 提取所有Concept
    concepts = extract_concepts_from_framework(framework)
    
    logger.info(
        "content_generation_node_start_v3_dual_checkpointer",
        task_id=task_id,
        roadmap_id=roadmap_id,
        concept_count=len(concepts),
        architecture="dual_checkpointer",
    )
    
    # ✅ 双 Checkpointer 架构：获取子图专用的 checkpointer
    child_checkpointer = ctx.child_checkpointer
    
    # ✅ 构建子图时传入独立的 checkpointer
    subgraph = build_content_generation_subgraph(checkpointer=child_checkpointer)
    
    # 准备子图输入状态
    sub_state = {
        "roadmap_id": roadmap_id,
        "concepts": concepts,
        "user_preferences": user_request.preferences,
        "task_id": task_id,
        "concept": None,  # 用于 Send API
        "concept_results": [],  # Reducer 自动累加
    }
    
    # ✅ 关键：为子图创建独立的 thread_id（添加 :child 后缀）
    # 这样主图和子图可以共享同一个 checkpointer，但通过不同的 thread_id 隔离状态
    # 主图 thread_id: {task_id}
    # 子图 thread_id: {task_id}:child
    child_config = {
        "configurable": {
            "thread_id": f"{task_id}:child",  # 添加 :child 后缀以区分主图和子图
            "runtime_context": config["configurable"]["runtime_context"],
        }
    }
    
    # LangGraph 会自动跳过已完成的节点，只执行失败的部分
    result = await subgraph.ainvoke(sub_state, child_config)
    
    # 统计结果
    concept_results = result.get("concept_results", [])
    successful_count = len([
        r for r in concept_results
        if r.get("save_status", {}).get("metadata_saved", False)
    ])
    failed_count = len(concept_results) - successful_count
    
    logger.info(
        "content_generation_node_completed_v3_dual_checkpointer",
        task_id=task_id,
        roadmap_id=roadmap_id,
        total_concepts=len(concept_results),
        successful_count=successful_count,
        failed_count=failed_count,
        architecture="dual_checkpointer",
    )
    
    # 构造主图状态更新（新架构不再返回 tutorial_refs 等字段）
    return {
        "roadmap_id": roadmap_id,
        "concept_results": concept_results,
        "current_step": "content_generation",
        "execution_history": [
            f"内容生成完成：成功 {successful_count}，失败 {failed_count}"
        ],
    }

