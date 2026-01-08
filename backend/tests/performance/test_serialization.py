"""
序列化性能基准测试

对比json vs msgspec的性能差异。
验证msgspec在大对象序列化场景下的性能提升（目标：5-10倍）。
"""
import pytest
import json
import time
from typing import Any

from app.utils.serializers import fast_dumps, fast_loads


def create_large_state(concepts_count: int = 100) -> dict[str, Any]:
    """
    创建模拟的LangGraph State对象
    
    模拟路线图生成时的State大小（100个概念，每个有详细元数据）
    
    Args:
        concepts_count: 概念数量
        
    Returns:
        模拟的State字典
    """
    return {
        "task_id": "test-task-123456",
        "roadmap_id": "roadmap-abc-def-ghi",
        "user_id": "user-789",
        "intent": {
            "goal": "学习 Python 后端开发",
            "current_level": "beginner",
            "time_available": "3-6个月",
            "learning_style": "项目驱动",
        },
        "concepts": [
            {
                "concept_id": f"concept-{i}",
                "title": f"概念标题 {i}",
                "description": "这是一个详细的概念描述，包含学习目标、关键知识点、实践建议等内容。" * 5,
                "order": i,
                "stage": i // 10,
                "dependencies": [f"concept-{j}" for j in range(max(0, i-3), i)],
                "metadata": {
                    "difficulty": "intermediate",
                    "estimated_hours": 8,
                    "resources_count": 5,
                    "quiz_questions": 10,
                },
                "content": {
                    "tutorial": "详细的教程内容..." * 20,
                    "resources": ["资源链接1", "资源链接2", "资源链接3"],
                    "quiz": {"questions": [f"问题{j}" for j in range(10)]},
                },
            }
            for i in range(concepts_count)
        ],
        "metadata": {
            "created_at": "2026-01-08T10:00:00",
            "updated_at": "2026-01-08T10:05:00",
            "version": "1.0",
            "total_concepts": concepts_count,
            "total_stages": concepts_count // 10,
        },
        "validation_results": {
            "passed": True,
            "issues": [],
            "suggestions": ["建议增加实践项目", "建议补充进阶资源"],
        },
    }


def test_msgspec_performance_basic():
    """基准测试：msgspec vs json（基本功能验证）"""
    # 准备测试数据
    data = {"user_id": "123", "roadmap_id": "abc", "concepts": [1, 2, 3]}
    
    # 测试序列化
    json_result = json.dumps(data)
    msgspec_result = fast_dumps(data)
    
    # msgspec返回bytes，json.dumps返回str
    assert isinstance(json_result, str)
    assert isinstance(msgspec_result, bytes)
    
    # 内容应该相同（除了格式）
    assert json.loads(json_result) == fast_loads(msgspec_result)
    
    print("✅ 基本功能验证通过")


def test_msgspec_performance_large_object():
    """基准测试：msgspec vs json（大对象性能对比）"""
    # 准备测试数据（模拟LangGraph State，100个概念）
    large_state = create_large_state(concepts_count=100)
    
    iterations = 1000  # 重复序列化1000次
    
    # ===== json.dumps 基准 =====
    start = time.time()
    for _ in range(iterations):
        json.dumps(large_state)
    json_time = time.time() - start
    
    # ===== msgspec 基准 =====
    start = time.time()
    for _ in range(iterations):
        fast_dumps(large_state)
    msgspec_time = time.time() - start
    
    # 计算性能提升倍数
    speedup = json_time / msgspec_time
    
    print(f"\n{'='*60}")
    print(f"序列化性能对比（{iterations}次迭代）")
    print(f"{'='*60}")
    print(f"测试数据大小: {len(json.dumps(large_state))} 字节")
    print(f"json.dumps 耗时: {json_time:.3f}秒")
    print(f"msgspec 耗时:    {msgspec_time:.3f}秒")
    print(f"性能提升:        {speedup:.1f}x")
    print(f"{'='*60}\n")
    
    # 验证性能提升至少5倍
    assert speedup > 5, f"msgspec性能提升不足：仅{speedup:.1f}x（预期>5x）"
    print(f"✅ 性能测试通过：msgspec比json.dumps快{speedup:.1f}倍")


def test_msgspec_performance_deserialization():
    """基准测试：msgspec vs json（反序列化性能对比）"""
    # 准备测试数据
    large_state = create_large_state(concepts_count=100)
    
    # 预先序列化
    json_data = json.dumps(large_state)
    msgspec_data = fast_dumps(large_state)
    
    iterations = 1000
    
    # ===== json.loads 基准 =====
    start = time.time()
    for _ in range(iterations):
        json.loads(json_data)
    json_time = time.time() - start
    
    # ===== msgspec 基准 =====
    start = time.time()
    for _ in range(iterations):
        fast_loads(msgspec_data)
    msgspec_time = time.time() - start
    
    # 计算性能提升倍数
    speedup = json_time / msgspec_time
    
    print(f"\n{'='*60}")
    print(f"反序列化性能对比（{iterations}次迭代）")
    print(f"{'='*60}")
    print(f"测试数据大小: {len(json_data)} 字节")
    print(f"json.loads 耗时: {json_time:.3f}秒")
    print(f"msgspec 耗时:    {msgspec_time:.3f}秒")
    print(f"性能提升:        {speedup:.1f}x")
    print(f"{'='*60}\n")
    
    # 验证性能提升至少5倍
    assert speedup > 5, f"msgspec反序列化性能提升不足：仅{speedup:.1f}x（预期>5x）"
    print(f"✅ 反序列化测试通过：msgspec比json.loads快{speedup:.1f}倍")


def test_msgspec_correctness():
    """正确性测试：验证msgspec序列化/反序列化的正确性"""
    # 准备复杂的测试数据
    test_cases = [
        # 基本类型
        {"int": 123, "float": 45.67, "str": "Hello", "bool": True, "none": None},
        # 嵌套结构
        {"nested": {"level1": {"level2": {"level3": "deep"}}}},
        # 列表和字典
        {"list": [1, 2, 3], "dict": {"a": 1, "b": 2}},
        # Unicode字符
        {"chinese": "你好世界", "emoji": "🚀✨"},
        # 大型对象
        create_large_state(concepts_count=50),
    ]
    
    for i, test_data in enumerate(test_cases):
        # 序列化 -> 反序列化
        serialized = fast_dumps(test_data)
        deserialized = fast_loads(serialized)
        
        # 验证数据完整性
        assert deserialized == test_data, f"测试用例{i+1}失败：数据不一致"
    
    print(f"✅ 正确性测试通过：所有{len(test_cases)}个测试用例均通过")


@pytest.mark.benchmark
def test_msgspec_real_world_scenario():
    """真实场景测试：模拟Redis缓存操作"""
    # 模拟10个并发任务的State缓存操作
    tasks_count = 10
    operations_per_task = 100  # 每个任务执行100次读写
    
    states = [create_large_state(concepts_count=50) for _ in range(tasks_count)]
    
    # ===== json 基准（旧代码）=====
    start = time.time()
    for task_state in states:
        for _ in range(operations_per_task):
            # 写入（序列化）
            serialized = json.dumps(task_state)
            # 读取（反序列化）
            json.loads(serialized)
    json_time = time.time() - start
    
    # ===== msgspec 基准（新代码）=====
    start = time.time()
    for task_state in states:
        for _ in range(operations_per_task):
            # 写入（序列化）
            serialized = fast_dumps(task_state)
            # 读取（反序列化）
            fast_loads(serialized)
    msgspec_time = time.time() - start
    
    # 计算性能提升
    speedup = json_time / msgspec_time
    total_operations = tasks_count * operations_per_task * 2  # 读写各一次
    
    print(f"\n{'='*60}")
    print(f"真实场景性能测试")
    print(f"{'='*60}")
    print(f"模拟场景: {tasks_count}个任务 × {operations_per_task}次操作")
    print(f"总操作数: {total_operations}次（读写各{total_operations//2}次）")
    print(f"json 总耗时:   {json_time:.3f}秒 ({total_operations/json_time:.0f} ops/s)")
    print(f"msgspec 总耗时: {msgspec_time:.3f}秒 ({total_operations/msgspec_time:.0f} ops/s)")
    print(f"性能提升:      {speedup:.1f}x")
    print(f"时间节省:      {json_time - msgspec_time:.3f}秒")
    print(f"{'='*60}\n")
    
    assert speedup > 5, f"真实场景性能提升不足：仅{speedup:.1f}x"
    print(f"✅ 真实场景测试通过：性能提升{speedup:.1f}倍")


if __name__ == "__main__":
    """直接运行此文件进行性能测试"""
    print("\n🚀 开始msgspec序列化性能测试...\n")
    
    test_msgspec_performance_basic()
    test_msgspec_correctness()
    test_msgspec_performance_large_object()
    test_msgspec_performance_deserialization()
    test_msgspec_real_world_scenario()
    
    print("\n✅ 所有性能测试完成！\n")

