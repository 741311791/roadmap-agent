"""
内容生成节点执行器（LangGraph 1.0 子图模式）

负责执行内容生成节点（Step 5: Content Generation）
使用 LangGraph 子图模式，实现细粒度 Checkpoint 和容错。

架构变化（LangGraph 1.0 迁移）：
- 旧方案: 发送独立 Celery 任务到 content_generation 队列
- 新方案: 调用 LangGraph 子图（在主 Graph 内执行）

优势：
- ✅ 细粒度 Checkpoint：每个 Concept 独立保存状态
- ✅ 单独重试：Tutorial 失败不影响 Resource 和 Quiz
- ✅ 统一容错：Node 级 RetryPolicy 自动处理失败
- ✅ 动态并行：Send API 根据 Concept 数量动态创建并行任务
"""
import structlog

from ..base import RoadmapState
from ..workflow_brain import WorkflowBrain
from ..subgraphs.content_generation import build_content_generation_subgraph

logger = structlog.get_logger()


def extract_concepts_from_framework(framework) -> list:
    """
    从路线图框架中提取所有 Concept
    
    Args:
        framework: RoadmapFramework 对象
        
    Returns:
        list[Concept]: Concept 列表
    """
    concepts = []
    for stage in framework.stages:
        for module in stage.modules:
            concepts.extend(module.concepts)
    return concepts


class ContentRunner:
    """
    内容生成节点执行器（LangGraph 1.0 子图模式）
    
    职责：
    1. 从 state 中提取路线图框架和用户偏好
    2. 提取所有 Concept 列表
    3. 调用内容生成子图（同步执行，在主 Graph 内）
    4. 处理子图返回的结果（tutorials、resources、quizzes、errors）
    5. 返回状态更新
    """
    
    def __init__(
        self,
        brain: WorkflowBrain,
    ):
        """
        Args:
            brain: WorkflowBrain 实例（统一协调者）
        """
        self.brain = brain
    
    async def run(self, state: RoadmapState) -> dict:
        """
        执行内容生成节点（子图模式）
        
        流程：
        1. 提取路线图框架和 Concept 列表
        2. 构造子图输入状态
        3. 调用子图执行（ainvoke）
        4. 处理子图返回的结果
        5. 返回主图状态更新
        
        Args:
            state: 当前工作流状态
            
        Returns:
            状态更新字典
        """
        async with self.brain.node_execution("content_generation", state):
            framework = state.get("roadmap_framework")
            if not framework:
                raise ValueError("路线图框架不存在，无法生成内容")
            
            roadmap_id = state.get("roadmap_id")
            if not roadmap_id:
                raise ValueError("roadmap_id 不存在，无法生成内容")
            
            task_id = state["task_id"]
            user_request = state["user_request"]
            
            # 提取所有 Concept
            concepts = extract_concepts_from_framework(framework)
            
            logger.info(
                "content_runner_starting_subgraph",
                task_id=task_id,
                roadmap_id=roadmap_id,
                concept_count=len(concepts),
            )
            
            # 构建子图
            subgraph = build_content_generation_subgraph()
            
            # 准备子图输入状态（传递 brain 和 agent_factory）
            sub_state = {
                "roadmap_id": roadmap_id,
                "concepts": concepts,
                "user_preferences": user_request.preferences,
                "task_id": task_id,
                "brain": self.brain,  # 传递 WorkflowBrain 实例
                "agent_factory": self.brain.agent_factory,  # 传递 AgentFactory 实例
                "concept": None,  # 用于 Send API
                "context": None,  # 用于 Send API
                "tutorials": [],
                "resources": [],
                "quizzes": [],
                "errors": [],
            }
            
            # 执行子图（会自动继承父图的 Checkpointer）
            result = await subgraph.ainvoke(sub_state)
            
            # 批量保存所有内容元数据到数据库
            await self._save_all_content_metadata(roadmap_id, result)
            
            # 更新 ConceptMetadata 状态字段
            await self._update_concept_metadata(roadmap_id, result)
            
            logger.info(
                "content_runner_subgraph_completed",
                task_id=task_id,
                tutorial_count=len(result["tutorials"]),
                resource_count=len(result["resources"]),
                quiz_count=len(result["quizzes"]),
                error_count=len(result["errors"]),
            )
            
            # 构造主图状态更新
            state_update = {
                "tutorial_refs": {
                    t.concept_id: t for t in result["tutorials"]
                },
                "resource_refs": {
                    r.concept_id: r for r in result["resources"]
                },
                "quiz_refs": {
                    q.concept_id: q for q in result["quizzes"]
                },
                "failed_concepts": [
                    e["concept_id"] for e in result["errors"]
                ],
                "current_step": "content_generation_completed",
                "execution_history": [
                    f"内容生成完成：教程 {len(result['tutorials'])}，资源 {len(result['resources'])}，测验 {len(result['quizzes'])}，失败 {len(result['errors'])}"
                ],
            }
            
            return state_update
