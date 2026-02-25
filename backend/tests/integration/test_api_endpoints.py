"""
API端点集成测试

验证接口调用和响应格式是否符合预期
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
class TestUserProfileEndpoints:
    """测试用户画像接口"""
    
    async def test_get_user_profile(self, client: AsyncClient, auth_headers: dict):
        """测试获取用户画像（从JWT提取user_id）"""
        response = await client.get(
            "/api/v1/users/profile",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "code" in data
        assert "msg" in data
        assert "data" in data
        assert data["code"] == 200
    
    async def test_update_user_profile(self, client: AsyncClient, auth_headers: dict):
        """测试更新用户画像（从JWT提取user_id）"""
        profile_data = {
            "industry": "Technology",
            "current_role": "Software Engineer",
            "tech_stack": [
                {
                    "technology": "Python",
                    "proficiency": "intermediate"
                }
            ],
            "primary_language": "zh",
            "weekly_commitment_hours": 10,
            "learning_style": ["text", "hands_on"],
            "ai_personalization": True,
        }
        
        response = await client.put(
            "/api/v1/users/profile",
            headers=auth_headers,
            json=profile_data,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data


@pytest.mark.asyncio
class TestRoadmapListEndpoints:
    """测试路线图列表接口"""
    
    async def test_get_my_roadmaps(self, client: AsyncClient, auth_headers: dict):
        """测试获取我的路线图列表（从JWT提取user_id）"""
        response = await client.get(
            "/api/v1/roadmaps/my",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "roadmaps" in data["data"]
        assert "total" in data["data"]
    
    async def test_get_trash(self, client: AsyncClient, auth_headers: dict):
        """测试获取回收站（从JWT提取user_id）"""
        response = await client.get(
            "/api/v1/roadmaps/trash",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data


@pytest.mark.asyncio
class TestRoadmapCRUDEndpoints:
    """测试路线图CRUD接口"""
    
    async def test_get_roadmap_status(self, client: AsyncClient, roadmap_id: str):
        """测试获取路线图状态"""
        response = await client.get(
            f"/api/v1/roadmaps/{roadmap_id}/status",
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 200
            assert "data" in data
            assert "roadmap_id" in data["data"]
            assert "status" in data["data"]
    
    async def test_get_roadmap_status_quick(self, client: AsyncClient, roadmap_id: str):
        """测试快速检查路线图状态"""
        response = await client.get(
            f"/api/v1/roadmaps/{roadmap_id}/status/quick",
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 200
            assert "data" in data
            assert "has_active_task" in data["data"]
            assert "zombie_count" in data["data"]


@pytest.mark.asyncio
class TestTaskEndpoints:
    """测试任务管理接口"""
    
    async def test_get_my_tasks(self, client: AsyncClient, auth_headers: dict):
        """测试获取我的任务列表（从JWT提取user_id）"""
        response = await client.get(
            "/api/v1/tasks/my",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "tasks" in data["data"]
        assert "total" in data["data"]
    
    async def test_get_content_generation_status(self, client: AsyncClient, task_id: str):
        """测试获取内容生成状态"""
        response = await client.get(
            f"/api/v1/tasks/{task_id}/content-status",
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 200
            assert "data" in data
            assert "task_id" in data["data"]
            assert "status" in data["data"]


@pytest.mark.asyncio
class TestMetadataEndpoints:
    """测试元数据查询接口"""
    
    async def test_get_edit_records_by_roadmap_id(self, client: AsyncClient, roadmap_id: str):
        """测试通过roadmap_id获取编辑记录"""
        response = await client.get(
            f"/api/v1/roadmaps/{roadmap_id}/edit-records",
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 200
            assert "data" in data
            assert "records" in data["data"]
    
    async def test_get_validation_records_by_roadmap_id(self, client: AsyncClient, roadmap_id: str):
        """测试通过roadmap_id获取验证记录"""
        response = await client.get(
            f"/api/v1/roadmaps/{roadmap_id}/validation-records",
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["code"] == 200
            assert "data" in data
            assert "records" in data["data"]


@pytest.mark.asyncio
class TestAdminEndpoints:
    """测试管理员接口"""
    
    async def test_invite_user(self, client: AsyncClient, admin_headers: dict):
        """测试邀请用户（新路径）"""
        response = await client.post(
            "/api/v1/admin/users/invite",
            headers=admin_headers,
            json={"email": "test@example.com"},
        )
        
        # 可能已存在或创建成功
        assert response.status_code in [200, 400]
    
    async def test_get_tavily_keys(self, client: AsyncClient, admin_headers: dict):
        """测试获取Tavily Keys（新路径）"""
        response = await client.get(
            "/api/v1/admin/tavily/keys",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200


@pytest.mark.asyncio
class TestAuthEndpoints:
    """测试认证接口"""
    
    async def test_logout(self, client: AsyncClient, auth_headers: dict):
        """测试登出"""
        response = await client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "message" in data["data"]
        assert "user_id" in data["data"]
    
    async def test_get_blacklist_stats(self, client: AsyncClient, admin_headers: dict):
        """测试获取黑名单统计"""
        response = await client.get(
            "/api/v1/auth/blacklist/stats",
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "total_tokens" in data["data"]
        assert "active_tokens" in data["data"]
        assert "expired_tokens" in data["data"]


@pytest.mark.asyncio
class TestWaitlistEndpoints:
    """测试Waitlist接口"""
    
    async def test_join_waitlist(self, client: AsyncClient):
        """测试加入候补名单（包含position字段）"""
        response = await client.post(
            "/api/v1/waitlist",
            json={"email": "newuser@example.com"},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "success" in data["data"]
        assert "message" in data["data"]
        assert "is_new" in data["data"]
        # position字段应该存在（如果是新用户）
        if data["data"]["is_new"]:
            assert "position" in data["data"]
            assert isinstance(data["data"]["position"], int)
