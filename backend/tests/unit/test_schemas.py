"""
测试所有Schema定义和序列化

验证新增和修改的Schema是否正确定义和序列化
"""
import pytest
from datetime import datetime
from app.schemas.roadmap import (
    RoadmapDetailResponse,
    RoadmapDeleteResponse,
    RoadmapRestoreResponse,
    RoadmapPermanentDeleteResponse,
    RoadmapStatusResponse,
    RoadmapStatusQuickResponse,
)
from app.schemas.auth import LogoutResponse, BlacklistStatsResponse
from app.schemas.task import ContentGenerationStatusResponse
from app.schemas.waitlist import WaitlistJoinResponse


class TestRoadmapSchemas:
    """测试路线图相关Schema"""
    
    def test_roadmap_detail_response(self):
        """测试RoadmapDetailResponse序列化"""
        data = RoadmapDetailResponse(
            roadmap_id="test-roadmap-001",
            user_id="user-123",
            learning_goal="学习Python Web开发",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            framework={"stages": []},
            status="completed",
            title="Python Web Development",
            description="从零开始学习Python Web开发",
        )
        
        assert data.roadmap_id == "test-roadmap-001"
        assert data.user_id == "user-123"
        assert data.status == "completed"
        assert isinstance(data.framework, dict)
    
    def test_roadmap_delete_response(self):
        """测试RoadmapDeleteResponse序列化"""
        data = RoadmapDeleteResponse(
            message="路线图已删除",
            roadmap_id="test-roadmap-001",
        )
        
        assert data.message == "路线图已删除"
        assert data.roadmap_id == "test-roadmap-001"
    
    def test_roadmap_restore_response(self):
        """测试RoadmapRestoreResponse序列化"""
        data = RoadmapRestoreResponse(
            message="路线图已恢复",
            roadmap_id="test-roadmap-001",
        )
        
        assert data.message == "路线图已恢复"
        assert data.roadmap_id == "test-roadmap-001"
    
    def test_roadmap_permanent_delete_response(self):
        """测试RoadmapPermanentDeleteResponse序列化"""
        data = RoadmapPermanentDeleteResponse(
            message="路线图已永久删除",
            roadmap_id="test-roadmap-001",
        )
        
        assert data.message == "路线图已永久删除"
        assert data.roadmap_id == "test-roadmap-001"
    
    def test_roadmap_status_response(self):
        """测试RoadmapStatusResponse序列化"""
        data = RoadmapStatusResponse(
            roadmap_id="test-roadmap-001",
            status="completed",
            task_id="task-123",
        )
        
        assert data.roadmap_id == "test-roadmap-001"
        assert data.status == "completed"
        assert data.task_id == "task-123"
        
        # 测试可选字段
        data_without_task = RoadmapStatusResponse(
            roadmap_id="test-roadmap-002",
            status="draft",
        )
        assert data_without_task.task_id is None
    
    def test_roadmap_status_quick_response(self):
        """测试RoadmapStatusQuickResponse序列化"""
        data = RoadmapStatusQuickResponse(
            roadmap_id="test-roadmap-001",
            status="completed",
            has_active_task=False,
            zombie_count=0,
        )
        
        assert data.roadmap_id == "test-roadmap-001"
        assert data.has_active_task is False
        assert data.zombie_count == 0
        
        # 测试包含僵尸概念的情况
        data_with_zombies = RoadmapStatusQuickResponse(
            roadmap_id="test-roadmap-002",
            status="processing",
            has_active_task=True,
            active_task_id="task-456",
            zombie_concepts=["concept-1", "concept-2"],
            zombie_count=2,
        )
        assert data_with_zombies.zombie_count == 2
        assert len(data_with_zombies.zombie_concepts) == 2


class TestAuthSchemas:
    """测试认证相关Schema"""
    
    def test_logout_response(self):
        """测试LogoutResponse序列化"""
        data = LogoutResponse(
            message="成功登出",
            user_id="user-123",
        )
        
        assert data.message == "成功登出"
        assert data.user_id == "user-123"
        assert data.devices_count is None
        
        # 测试包含设备数量
        data_with_devices = LogoutResponse(
            message="已登出所有设备",
            user_id="user-123",
            devices_count=3,
        )
        assert data_with_devices.devices_count == 3
    
    def test_blacklist_stats_response(self):
        """测试BlacklistStatsResponse序列化"""
        data = BlacklistStatsResponse(
            total_tokens=100,
            active_tokens=80,
            expired_tokens=20,
        )
        
        assert data.total_tokens == 100
        assert data.active_tokens == 80
        assert data.expired_tokens == 20


class TestTaskSchemas:
    """测试任务相关Schema"""
    
    def test_content_generation_status_response(self):
        """测试ContentGenerationStatusResponse序列化"""
        data = ContentGenerationStatusResponse(
            task_id="task-123",
            celery_task_id="celery-456",
            status="PROGRESS",
            progress={"current": 15, "total": 30, "percentage": 50.0},
            message="正在生成教程内容",
        )
        
        assert data.task_id == "task-123"
        assert data.celery_task_id == "celery-456"
        assert data.status == "PROGRESS"
        assert data.progress["percentage"] == 50.0
        assert data.message == "正在生成教程内容"
        
        # 测试可选字段
        data_minimal = ContentGenerationStatusResponse(
            task_id="task-789",
            status="PENDING",
        )
        assert data_minimal.celery_task_id is None
        assert data_minimal.progress is None


class TestWaitlistSchemas:
    """测试Waitlist相关Schema"""
    
    def test_waitlist_join_response(self):
        """测试WaitlistJoinResponse序列化"""
        data = WaitlistJoinResponse(
            success=True,
            message="Thanks for joining!",
            is_new=True,
            position=42,
        )
        
        assert data.success is True
        assert data.is_new is True
        assert data.position == 42
        
        # 测试可选字段
        data_without_position = WaitlistJoinResponse(
            success=True,
            message="Already on waitlist",
            is_new=False,
        )
        assert data_without_position.position is None


class TestSchemaJsonSerialization:
    """测试Schema的JSON序列化和反序列化"""
    
    def test_roadmap_detail_json_serialization(self):
        """测试RoadmapDetailResponse的JSON序列化"""
        data = RoadmapDetailResponse(
            roadmap_id="test-001",
            user_id="user-123",
            learning_goal="学习Python",
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            framework={"stages": [{"name": "基础阶段"}]},
            status="completed",
        )
        
        # 序列化为JSON
        json_str = data.model_dump_json()
        assert isinstance(json_str, str)
        
        # 反序列化
        parsed = RoadmapDetailResponse.model_validate_json(json_str)
        assert parsed.roadmap_id == data.roadmap_id
        assert parsed.framework == data.framework
    
    def test_content_generation_status_json_serialization(self):
        """测试ContentGenerationStatusResponse的JSON序列化"""
        data = ContentGenerationStatusResponse(
            task_id="task-123",
            status="SUCCESS",
            result={"completed_concepts": 10},
        )
        
        json_str = data.model_dump_json()
        parsed = ContentGenerationStatusResponse.model_validate_json(json_str)
        assert parsed.task_id == data.task_id
        assert parsed.result["completed_concepts"] == 10
