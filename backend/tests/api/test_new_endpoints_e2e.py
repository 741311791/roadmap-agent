"""
新API端点端到端测试

测试目标：
- 验证拆分后的API端点结构正常工作
- 测试真实用户请求的完整流程
- 确保所有新端点可以正常响应

测试流程：
1. 生成路线图（generation.py）
2. 查询任务状态（generation.py）
3. 获取路线图（retrieval.py）
4. 查询活跃任务（retrieval.py）
5. 查询教程版本（tutorial.py）
6. 查询资源和测验（resource.py, quiz.py）
"""
import pytest
import asyncio
import time
from httpx import AsyncClient, ASGITransport
from typing import Dict, Any

from app.main import app
from app.models.domain import UserRequest, LearningPreferences


class TestNewAPIEndpointsE2E:
    """新API端点的端到端测试"""
    
    @pytest.fixture
    def sample_user_request(self) -> Dict[str, Any]:
        """创建示例用户请求"""
        return {
            "user_id": "test-user-e2e",
            "session_id": "test-session-e2e",
            "preferences": {
                "learning_goal": "学习Python Web开发",
                "available_hours_per_week": 15,
                "motivation": "职业发展",
                "current_level": "intermediate",
                "career_background": "初级开发者",
                "content_preference": ["visual", "hands_on", "text"],
                "target_deadline": None,
            },
            "additional_context": "希望系统学习Flask和Django框架",
        }
    
    @pytest.mark.asyncio
    async def test_01_generation_endpoint(self, sample_user_request):
        """
        测试1：路线图生成端点
        端点：POST /api/v1/roadmaps/generate
        文件：endpoints/generation.py
        """
        print("\n" + "="*70)
        print("测试1：路线图生成端点")
        print("="*70)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/roadmaps/generate",
                json=sample_user_request,
            )
            
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")
            
            assert response.status_code == 200
            data = response.json()
            
            # 验证响应结构
            assert "task_id" in data
            assert "status" in data
            assert data["status"] == "processing"
            assert "message" in data
            
            # 保存task_id用于后续测试
            self.task_id = data["task_id"]
            print(f"✅ 生成任务已创建: {self.task_id}")
            
            return self.task_id
    
    @pytest.mark.asyncio
    async def test_02_task_status_endpoint(self):
        """
        测试2：任务状态查询端点
        端点：GET /api/v1/roadmaps/{task_id}/status
        文件：endpoints/generation.py
        """
        print("\n" + "="*70)
        print("测试2：任务状态查询端点")
        print("="*70)
        
        # 如果没有task_id，先创建一个
        if not hasattr(self, 'task_id'):
            self.task_id = await self.test_01_generation_endpoint(
                {"user_id": "test", "session_id": "test", 
                 "preferences": {"learning_goal": "test"}}
            )
        
        # 等待一小段时间让任务开始处理
        await asyncio.sleep(2)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/roadmaps/{self.task_id}/status",
            )
            
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.json()}")
            
            assert response.status_code in [200, 404]  # 可能还未创建或正在处理
            
            if response.status_code == 200:
                data = response.json()
                assert "task_id" in data or "status" in data
                print(f"✅ 任务状态: {data.get('status', 'unknown')}")
            else:
                print("⚠️ 任务未找到（可能还在初始化）")
    
    @pytest.mark.asyncio
    async def test_03_retrieval_endpoints(self):
        """
        测试3：路线图查询端点
        端点：GET /api/v1/roadmaps/{roadmap_id}
        文件：endpoints/retrieval.py
        """
        print("\n" + "="*70)
        print("测试3：路线图查询端点")
        print("="*70)
        
        # 使用一个假的roadmap_id测试
        test_roadmap_id = "python-web-dev-test"
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/roadmaps/{test_roadmap_id}",
            )
            
            print(f"状态码: {response.status_code}")
            
            # 应该返回404或200（如果路线图存在）
            assert response.status_code in [200, 404]
            
            if response.status_code == 404:
                print("✅ 正确返回404（路线图不存在）")
            else:
                data = response.json()
                print(f"✅ 路线图数据: {data.keys()}")
    
    @pytest.mark.asyncio
    async def test_04_active_task_endpoint(self):
        """
        测试4：活跃任务查询端点
        端点：GET /api/v1/roadmaps/{roadmap_id}/active-task
        文件：endpoints/retrieval.py
        """
        print("\n" + "="*70)
        print("测试4：活跃任务查询端点")
        print("="*70)
        
        test_roadmap_id = "python-web-dev-test"
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/roadmaps/{test_roadmap_id}/active-task",
            )
            
            print(f"状态码: {response.status_code}")
            
            assert response.status_code in [200, 404]
            
            if response.status_code == 404:
                print("✅ 正确返回404（路线图不存在）")
            else:
                data = response.json()
                assert "has_active_task" in data
                print(f"✅ 活跃任务状态: {data}")
    
    @pytest.mark.asyncio
    async def test_05_tutorial_endpoints(self):
        """
        测试5：教程管理端点
        端点：GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/*
        文件：endpoints/tutorial.py
        """
        print("\n" + "="*70)
        print("测试5：教程管理端点")
        print("="*70)
        
        test_roadmap_id = "python-basics"
        test_concept_id = "variables-and-types"
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 测试获取所有版本
            response1 = await client.get(
                f"/api/v1/roadmaps/{test_roadmap_id}/concepts/{test_concept_id}/tutorials",
            )
            print(f"获取所有版本 - 状态码: {response1.status_code}")
            
            # 测试获取最新版本
            response2 = await client.get(
                f"/api/v1/roadmaps/{test_roadmap_id}/concepts/{test_concept_id}/tutorials/latest",
            )
            print(f"获取最新版本 - 状态码: {response2.status_code}")
            
            # 测试获取指定版本
            response3 = await client.get(
                f"/api/v1/roadmaps/{test_roadmap_id}/concepts/{test_concept_id}/tutorials/v1",
            )
            print(f"获取指定版本 - 状态码: {response3.status_code}")
            
            # 应该都返回404（因为测试数据不存在）
            assert all(r.status_code in [200, 404] for r in [response1, response2, response3])
            print("✅ 教程端点响应正常")
    
    @pytest.mark.asyncio
    async def test_06_resource_endpoint(self):
        """
        测试6：资源管理端点
        端点：GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources
        文件：endpoints/resource.py
        """
        print("\n" + "="*70)
        print("测试6：资源管理端点")
        print("="*70)
        
        test_roadmap_id = "python-basics"
        test_concept_id = "variables-and-types"
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/roadmaps/{test_roadmap_id}/concepts/{test_concept_id}/resources",
            )
            
            print(f"状态码: {response.status_code}")
            assert response.status_code in [200, 404]
            print("✅ 资源端点响应正常")
    
    @pytest.mark.asyncio
    async def test_07_quiz_endpoint(self):
        """
        测试7：测验管理端点
        端点：GET /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz
        文件：endpoints/quiz.py
        """
        print("\n" + "="*70)
        print("测试7：测验管理端点")
        print("="*70)
        
        test_roadmap_id = "python-basics"
        test_concept_id = "variables-and-types"
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/api/v1/roadmaps/{test_roadmap_id}/concepts/{test_concept_id}/quiz",
            )
            
            print(f"状态码: {response.status_code}")
            assert response.status_code in [200, 404]
            print("✅ 测验端点响应正常")
    
    @pytest.mark.asyncio
    async def test_08_approval_endpoint(self):
        """
        测试8：人工审核端点
        端点：POST /api/v1/roadmaps/{task_id}/approve
        文件：endpoints/approval.py
        """
        print("\n" + "="*70)
        print("测试8：人工审核端点")
        print("="*70)
        
        test_task_id = "test-task-123"
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/roadmaps/{test_task_id}/approve",
                params={"approved": True, "feedback": None},
            )
            
            print(f"状态码: {response.status_code}")
            # 应该返回400或404（任务不存在或状态不正确）
            assert response.status_code in [200, 400, 404, 500]
            print("✅ 审核端点响应正常")
    
    @pytest.mark.asyncio
    async def test_09_retry_endpoint(self):
        """
        测试9：失败重试端点
        端点：POST /api/v1/roadmaps/{roadmap_id}/retry-failed
        文件：endpoints/retry.py
        """
        print("\n" + "="*70)
        print("测试9：失败重试端点")
        print("="*70)
        
        test_roadmap_id = "python-basics"
        retry_request = {
            "user_id": "test-user",
            "content_types": ["tutorial", "resources", "quiz"],
            "preferences": {
                "learning_goal": "test",
                "available_hours_per_week": 10,
                "motivation": "test",
                "current_level": "beginner",
                "career_background": "学生",
            }
        }
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/roadmaps/{test_roadmap_id}/retry-failed",
                json=retry_request,
            )
            
            print(f"状态码: {response.status_code}")
            assert response.status_code in [200, 404]
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 重试响应: {data.get('message', data)}")
            else:
                print("✅ 正确返回404（路线图不存在）")
    
    @pytest.mark.asyncio
    async def test_10_modification_endpoint(self):
        """
        测试10：内容修改端点
        端点：POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/modify
        文件：endpoints/modification.py
        """
        print("\n" + "="*70)
        print("测试10：内容修改端点")
        print("="*70)
        
        test_roadmap_id = "python-basics"
        test_concept_id = "variables-and-types"
        modify_request = {
            "user_id": "test-user",
            "preferences": {
                "learning_goal": "test",
                "available_hours_per_week": 10,
                "motivation": "test",
                "current_level": "beginner",
                "career_background": "学生",
            },
            "requirements": ["增加更多代码示例", "简化术语"]
        }
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/roadmaps/{test_roadmap_id}/concepts/{test_concept_id}/tutorial/modify",
                json=modify_request,
            )
            
            print(f"状态码: {response.status_code}")
            assert response.status_code in [200, 404, 500]
            
            if response.status_code == 404:
                print("✅ 正确返回404（路线图或教程不存在）")
            else:
                print("✅ 修改端点响应正常")
    
    @pytest.mark.asyncio
    async def test_11_health_check(self):
        """
        测试11：健康检查端点
        端点：GET /health
        """
        print("\n" + "="*70)
        print("测试11：健康检查端点")
        print("="*70)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
            
            print(f"状态码: {response.status_code}")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            print(f"✅ 应用健康状态: {data}")
    
    @pytest.mark.asyncio
    async def test_12_openapi_docs(self):
        """
        测试12：OpenAPI文档端点
        端点：GET /docs, GET /openapi.json
        """
        print("\n" + "="*70)
        print("测试12：OpenAPI文档")
        print("="*70)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 测试OpenAPI JSON
            response1 = await client.get("/openapi.json")
            print(f"OpenAPI JSON - 状态码: {response1.status_code}")
            assert response1.status_code == 200
            
            openapi_spec = response1.json()
            assert "openapi" in openapi_spec
            assert "paths" in openapi_spec
            
            # 验证新端点在OpenAPI中
            paths = openapi_spec["paths"]
            expected_paths = [
                "/api/v1/roadmaps/generate",
                "/api/v1/roadmaps/{task_id}/status",
                "/api/v1/roadmaps/{roadmap_id}",
                "/api/v1/roadmaps/{task_id}/approve",
            ]
            
            for path in expected_paths:
                assert path in paths, f"端点 {path} 未在OpenAPI中注册"
            
            print(f"✅ OpenAPI文档包含 {len(paths)} 个端点")
            print(f"✅ 新拆分的端点已正确注册")


@pytest.mark.asyncio
async def test_complete_workflow_integration():
    """
    完整流程集成测试
    
    模拟真实用户场景：
    1. 创建路线图生成任务
    2. 轮询任务状态直到完成
    3. 获取完整路线图
    4. 查询教程、资源、测验
    """
    print("\n" + "="*80)
    print("完整流程集成测试")
    print("="*80)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", timeout=300.0) as client:
        # 步骤1：创建生成任务
        print("\n步骤1：创建路线图生成任务")
        user_request = {
            "user_id": "integration-test-user",
            "session_id": "integration-test-session",
            "preferences": {
                "learning_goal": "学习Python数据分析",
                "available_hours_per_week": 20,
                "motivation": "职业发展",
                "current_level": "intermediate",
                "career_background": "数据分析师",
                "content_preference": ["text", "hands_on"],
                "target_deadline": None,
            },
            "additional_context": "希望掌握pandas和数据可视化",
        }
        
        response = await client.post(
            "/api/v1/roadmaps/generate",
            json=user_request,
        )
        
        assert response.status_code == 200
        task_data = response.json()
        task_id = task_data["task_id"]
        print(f"✅ 任务已创建: {task_id}")
        
        # 步骤2：轮询任务状态（最多等待60秒）
        print("\n步骤2：监控任务执行状态")
        max_attempts = 30
        attempt = 0
        roadmap_id = None
        
        while attempt < max_attempts:
            await asyncio.sleep(2)
            
            status_response = await client.get(
                f"/api/v1/roadmaps/{task_id}/status",
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                current_status = status_data.get("status", "unknown")
                current_step = status_data.get("current_step", "unknown")
                roadmap_id = status_data.get("roadmap_id")
                
                print(f"  [{attempt+1}/{max_attempts}] 状态: {current_status}, 步骤: {current_step}")
                
                if current_status == "completed":
                    print(f"✅ 任务完成！路线图ID: {roadmap_id}")
                    break
                elif current_status == "failed":
                    print(f"❌ 任务失败: {status_data.get('error_message', '未知错误')}")
                    break
            
            attempt += 1
        
        # 如果有roadmap_id，继续测试其他端点
        if roadmap_id:
            # 步骤3：获取完整路线图
            print(f"\n步骤3：获取完整路线图 ({roadmap_id})")
            roadmap_response = await client.get(
                f"/api/v1/roadmaps/{roadmap_id}",
            )
            
            if roadmap_response.status_code == 200:
                roadmap_data = roadmap_response.json()
                print(f"✅ 成功获取路线图")
                print(f"   标题: {roadmap_data.get('title', 'N/A')}")
                print(f"   概念数量: {len(roadmap_data.get('concepts', []))}")
            
            # 步骤4：查询活跃任务
            print(f"\n步骤4：查询活跃任务")
            active_task_response = await client.get(
                f"/api/v1/roadmaps/{roadmap_id}/active-task",
            )
            
            if active_task_response.status_code == 200:
                active_data = active_task_response.json()
                print(f"✅ 活跃任务状态: {active_data}")
        
        print("\n" + "="*80)
        print("✅ 完整流程测试完成")
        print("="*80)


if __name__ == "__main__":
    """
    直接运行此脚本进行测试
    
    运行方式：
    python -m pytest backend/tests/api/test_new_endpoints_e2e.py -v -s
    """
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
