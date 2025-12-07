"""
测试新的 Orchestrator 组件（单元测试）

测试内容：
- StateManager
- WorkflowConfig
- WorkflowRouter
- 辅助函数（merge_dicts, ensure_unique_roadmap_id）
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.orchestrator.base import (
    RoadmapState,
    WorkflowConfig,
    merge_dicts,
    ensure_unique_roadmap_id,
)
from app.core.orchestrator.state_manager import StateManager
from app.core.orchestrator.routers import WorkflowRouter


class TestStateManager:
    """测试 StateManager"""
    
    def test_set_and_get_live_step(self):
        """测试设置和获取 live_step"""
        manager = StateManager()
        
        # 设置步骤
        manager.set_live_step("test-trace-001", "intent_analysis")
        
        # 获取步骤
        step = manager.get_live_step("test-trace-001")
        assert step == "intent_analysis"
    
    def test_get_nonexistent_live_step(self):
        """测试获取不存在的 live_step"""
        manager = StateManager()
        step = manager.get_live_step("nonexistent")
        assert step is None
    
    def test_clear_live_step(self):
        """测试清除 live_step"""
        manager = StateManager()
        
        manager.set_live_step("test-trace-001", "intent_analysis")
        manager.clear_live_step("test-trace-001")
        
        step = manager.get_live_step("test-trace-001")
        assert step is None
    
    def test_get_all_live_steps(self):
        """测试获取所有 live_step"""
        manager = StateManager()
        
        manager.set_live_step("trace-1", "step-1")
        manager.set_live_step("trace-2", "step-2")
        
        all_steps = manager.get_all_live_steps()
        assert len(all_steps) == 2
        assert all_steps["trace-1"] == "step-1"
        assert all_steps["trace-2"] == "step-2"
    
    def test_clear_all(self):
        """测试清除所有缓存"""
        manager = StateManager()
        
        manager.set_live_step("trace-1", "step-1")
        manager.set_live_step("trace-2", "step-2")
        manager.clear_all()
        
        all_steps = manager.get_all_live_steps()
        assert len(all_steps) == 0


class TestWorkflowConfig:
    """测试 WorkflowConfig"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = WorkflowConfig()
        
        assert config.skip_structure_validation is False
        assert config.skip_human_review is False
        assert config.skip_tutorial_generation is False
        assert config.skip_resource_recommendation is False
        assert config.skip_quiz_generation is False
        assert config.max_framework_retry == 3
        assert config.parallel_tutorial_limit == 5
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = WorkflowConfig(
            skip_structure_validation=True,
            skip_human_review=True,
            max_framework_retry=5,
        )
        
        assert config.skip_structure_validation is True
        assert config.skip_human_review is True
        assert config.max_framework_retry == 5


class TestWorkflowRouter:
    """测试 WorkflowRouter"""
    
    def test_route_after_validation_failed_retry(self, sample_roadmap_framework):
        """测试验证失败时的路由（需要重试）"""
        config = WorkflowConfig(max_framework_retry=3)
        router = WorkflowRouter(config)
        
        # 验证失败，修改次数 < 最大重试
        state = {
            "task_id": "test-trace",
            "validation_result": MagicMock(is_valid=False),
            "modification_count": 1,
            "roadmap_framework": sample_roadmap_framework,
        }
        
        result = router.route_after_validation(state)
        assert result == "edit_roadmap"
    
    def test_route_after_validation_max_retries(self):
        """测试验证失败达到最大重试次数"""
        config = WorkflowConfig(
            max_framework_retry=3,
            skip_human_review=False,
        )
        router = WorkflowRouter(config)
        
        # 验证失败，达到最大重试
        state = {
            "task_id": "test-trace",
            "validation_result": MagicMock(is_valid=False),
            "modification_count": 3,
        }
        
        result = router.route_after_validation(state)
        assert result == "human_review"
    
    def test_route_after_validation_success(self):
        """测试验证通过的路由"""
        config = WorkflowConfig(skip_human_review=False)
        router = WorkflowRouter(config)
        
        # 验证通过
        state = {
            "task_id": "test-trace",
            "validation_result": MagicMock(is_valid=True),
            "modification_count": 0,
        }
        
        result = router.route_after_validation(state)
        assert result == "human_review"
    
    def test_route_after_validation_skip_human_review(self):
        """测试跳过人工审核的路由"""
        config = WorkflowConfig(
            skip_human_review=True,
            skip_tutorial_generation=False,
        )
        router = WorkflowRouter(config)
        
        state = {
            "task_id": "test-trace",
            "validation_result": MagicMock(is_valid=True),
            "modification_count": 0,
        }
        
        result = router.route_after_validation(state)
        assert result == "tutorial_generation"
    
    def test_route_after_human_review_approved(self):
        """测试人工审核批准"""
        config = WorkflowConfig(skip_tutorial_generation=False)
        router = WorkflowRouter(config)
        
        state = {
            "task_id": "test-trace",
            "human_approved": True,
        }
        
        result = router.route_after_human_review(state)
        assert result == "approved"
    
    def test_route_after_human_review_rejected(self):
        """测试人工审核拒绝"""
        config = WorkflowConfig()
        router = WorkflowRouter(config)
        
        state = {
            "task_id": "test-trace",
            "human_approved": False,
        }
        
        result = router.route_after_human_review(state)
        assert result == "modify"


class TestHelperFunctions:
    """测试辅助函数"""
    
    def test_merge_dicts(self):
        """测试字典合并"""
        left = {"a": 1, "b": 2}
        right = {"c": 3, "d": 4}
        
        result = merge_dicts(left, right)
        assert result == {"a": 1, "b": 2, "c": 3, "d": 4}
    
    def test_merge_dicts_override(self):
        """测试字典合并（覆盖）"""
        left = {"a": 1, "b": 2}
        right = {"b": 3, "c": 4}
        
        result = merge_dicts(left, right)
        assert result == {"a": 1, "b": 3, "c": 4}
    
    @pytest.mark.asyncio
    async def test_ensure_unique_roadmap_id_unique(self):
        """测试 roadmap_id 唯一（不重复）"""
        # Mock repository
        mock_repo = MagicMock()
        mock_repo.roadmap_id_exists = AsyncMock(return_value=False)
        
        roadmap_id = "test-roadmap-12345678"
        result = await ensure_unique_roadmap_id(roadmap_id, mock_repo)
        
        assert result == roadmap_id
        mock_repo.roadmap_id_exists.assert_called_once_with(roadmap_id)
    
    @pytest.mark.asyncio
    async def test_ensure_unique_roadmap_id_duplicate(self):
        """测试 roadmap_id 重复（需要生成新ID）"""
        # Mock repository
        mock_repo = MagicMock()
        # 第一次检查：原ID存在
        # 第二次检查：新ID不存在
        mock_repo.roadmap_id_exists = AsyncMock(side_effect=[True, False])
        
        roadmap_id = "test-roadmap-12345678"
        result = await ensure_unique_roadmap_id(roadmap_id, mock_repo)
        
        # 应该返回不同的ID
        assert result != roadmap_id
        # 应该保留基础部分
        assert result.startswith("test-roadmap-")
        # 应该有8位后缀
        assert len(result.split("-")[-1]) == 8

