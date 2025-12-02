"""
测试 concept 详情页的 quiz 和 resources API

用法：
    cd backend
    uv run python scripts/test_concept_details_api.py
"""
import asyncio
import httpx
import json
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"


async def test_concept_quiz_resources(roadmap_id: str, concept_id: str):
    """测试获取 concept 的 quiz 和 resources"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"\n{'='*80}")
        print(f"Testing Concept Details API")
        print(f"Roadmap ID: {roadmap_id}")
        print(f"Concept ID: {concept_id}")
        print(f"{'='*80}\n")
        
        # 1. Test Quiz API
        print("1. Testing Quiz API...")
        try:
            response = await client.get(
                f"{BASE_URL}/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz"
            )
            
            if response.status_code == 200:
                quiz_data = response.json()
                print(f"✅ Quiz API Success")
                print(f"   Quiz ID: {quiz_data.get('quiz_id')}")
                print(f"   Total Questions: {quiz_data.get('total_questions')}")
                print(f"   Easy: {quiz_data.get('easy_count')}, Medium: {quiz_data.get('medium_count')}, Hard: {quiz_data.get('hard_count')}")
                print(f"   Generated At: {quiz_data.get('generated_at')}")
                
                # Show first question
                if quiz_data.get('questions'):
                    q = quiz_data['questions'][0]
                    print(f"\n   Sample Question:")
                    print(f"   - Type: {q.get('question_type')}")
                    print(f"   - Question: {q.get('question')[:80]}...")
                    print(f"   - Options: {len(q.get('options', []))} options")
                    print(f"   - Difficulty: {q.get('difficulty')}")
            elif response.status_code == 404:
                print(f"❌ Quiz Not Found (404)")
                print(f"   Message: {response.json().get('detail')}")
            else:
                print(f"❌ Quiz API Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Quiz API Error: {e}")
        
        print()
        
        # 2. Test Resources API
        print("2. Testing Resources API...")
        try:
            response = await client.get(
                f"{BASE_URL}/roadmaps/{roadmap_id}/concepts/{concept_id}/resources"
            )
            
            if response.status_code == 200:
                resources_data = response.json()
                print(f"✅ Resources API Success")
                print(f"   Resources ID: {resources_data.get('resources_id')}")
                print(f"   Resources Count: {resources_data.get('resources_count')}")
                print(f"   Generated At: {resources_data.get('generated_at')}")
                
                # Show first resource
                if resources_data.get('resources'):
                    r = resources_data['resources'][0]
                    print(f"\n   Sample Resource:")
                    print(f"   - Title: {r.get('title')}")
                    print(f"   - Type: {r.get('type')}")
                    print(f"   - URL: {r.get('url')[:60]}...")
                    print(f"   - Relevance: {r.get('relevance_score')}")
                    print(f"   - Description: {r.get('description')[:80]}...")
            elif response.status_code == 404:
                print(f"❌ Resources Not Found (404)")
                print(f"   Message: {response.json().get('detail')}")
            else:
                print(f"❌ Resources API Failed: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Resources API Error: {e}")
        
        print()
        
        # 3. Test Tutorial API (bonus check)
        print("3. Testing Tutorial API (bonus)...")
        try:
            response = await client.get(
                f"{BASE_URL}/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest"
            )
            
            if response.status_code == 200:
                tutorial_data = response.json()
                print(f"✅ Tutorial API Success")
                print(f"   Tutorial ID: {tutorial_data.get('tutorial_id')}")
                print(f"   Title: {tutorial_data.get('title')}")
                print(f"   Version: v{tutorial_data.get('content_version')}")
                print(f"   Content URL: {tutorial_data.get('content_url')[:60]}...")
            elif response.status_code == 404:
                print(f"❌ Tutorial Not Found (404)")
            else:
                print(f"❌ Tutorial API Failed: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Tutorial API Error: {e}")


async def list_available_concepts():
    """列出数据库中可用的 roadmap 和 concept"""
    print("\n" + "="*80)
    print("Listing Available Roadmaps and Concepts")
    print("="*80 + "\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Try to get a list of roadmaps from tasks
        try:
            # This is a simplified approach - in production you'd have a proper endpoint
            print("💡 To find available roadmaps and concepts:")
            print("   1. Check your database: SELECT roadmap_id FROM roadmap_metadata LIMIT 5;")
            print("   2. For each roadmap, check framework_data JSON for concept_ids")
            print("   3. Or use the /roadmaps/{roadmap_id} endpoint to see full structure")
            print()
            
        except Exception as e:
            print(f"Error: {e}")


async def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 3:
        print("❌ Missing arguments!")
        print()
        print("Usage:")
        print("  uv run python scripts/test_concept_details_api.py <roadmap_id> <concept_id>")
        print()
        print("Example:")
        print("  uv run python scripts/test_concept_details_api.py rm-abc123 concept-html-basics")
        print()
        
        await list_available_concepts()
        return
    
    roadmap_id = sys.argv[1]
    concept_id = sys.argv[2]
    
    await test_concept_quiz_resources(roadmap_id, concept_id)
    
    print("\n" + "="*80)
    print("Test Complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

