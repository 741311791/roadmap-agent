"""
验证datetime时区修复

测试点：
1. QuizGenerationOutput 生成的 created_at 是否无时区
2. _ensure_naive_datetime 函数能否正确处理带时区的datetime
3. 数据库插入是否成功
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from datetime import datetime, timezone, timedelta
from app.models.domain import QuizGenerationOutput, QuizQuestion
from app.crud.crud_quiz import _ensure_naive_datetime


def test_quiz_output_created_at():
    """测试1: QuizGenerationOutput 的 created_at 字段是否无时区"""
    print("\n=== 测试1: QuizGenerationOutput.created_at 时区检查 ===")
    
    quiz_output = QuizGenerationOutput(
        concept_id="test-concept",
        quiz_id="test-quiz-id",
        questions=[
            QuizQuestion(
                question_id="q1",
                question_type="single_choice",
                question="测试题目",
                options=["A", "B", "C"],
                correct_answer=[0],  # 正确答案索引列表
                explanation="测试解析",
                difficulty="easy",
            )
        ],
        total_questions=1,
    )
    
    created_at = quiz_output.created_at
    
    print(f"✅ created_at 值: {created_at}")
    print(f"✅ 时区信息 (tzinfo): {created_at.tzinfo}")
    
    if created_at.tzinfo is None:
        print("✅ 通过: created_at 无时区信息")
        return True
    else:
        print(f"❌ 失败: created_at 有时区信息 {created_at.tzinfo}")
        return False


def test_ensure_naive_datetime():
    """测试2: _ensure_naive_datetime 函数是否正确处理带时区datetime"""
    print("\n=== 测试2: _ensure_naive_datetime 函数测试 ===")
    
    # 测试2.1: 无时区datetime
    naive_dt = datetime(2024, 6, 15, 12, 0)
    result1 = _ensure_naive_datetime(naive_dt)
    print(f"✅ 输入（无时区）: {naive_dt}, tzinfo={naive_dt.tzinfo}")
    print(f"✅ 输出: {result1}, tzinfo={result1.tzinfo}")
    assert result1.tzinfo is None, "无时区datetime应保持无时区"
    assert result1 == naive_dt, "无时区datetime值应不变"
    print("✅ 通过: 无时区datetime保持不变")
    
    # 测试2.2: UTC时区datetime
    utc_dt = datetime(2024, 6, 15, 4, 0, tzinfo=timezone.utc)  # UTC 4:00
    result2 = _ensure_naive_datetime(utc_dt)
    print(f"\n✅ 输入（UTC）: {utc_dt}, tzinfo={utc_dt.tzinfo}")
    print(f"✅ 输出: {result2}, tzinfo={result2.tzinfo}")
    assert result2.tzinfo is None, "应移除时区信息"
    # UTC 4:00 = 北京时间 12:00
    assert result2.hour == 12, f"UTC 4:00应转换为北京时间12:00，实际{result2.hour}:00"
    print("✅ 通过: UTC时区正确转换为北京时间并移除时区")
    
    # 测试2.3: 自定义时区datetime (模拟错误场景)
    custom_tz = timezone(timedelta(hours=0))  # TzInfo(0)
    custom_dt = datetime(2024, 6, 15, 12, 0, tzinfo=custom_tz)
    result3 = _ensure_naive_datetime(custom_dt)
    print(f"\n✅ 输入（TzInfo(0)）: {custom_dt}, tzinfo={custom_dt.tzinfo}")
    print(f"✅ 输出: {result3}, tzinfo={result3.tzinfo}")
    assert result3.tzinfo is None, "应移除时区信息"
    # TzInfo(0) = UTC，转换后应该是北京时间 20:00
    assert result3.hour == 20, f"UTC 12:00应转换为北京时间20:00，实际{result3.hour}:00"
    print("✅ 通过: TzInfo(0)时区正确转换为北京时间并移除时区")
    
    return True


def test_database_compatibility():
    """测试3: 验证修复后的datetime可以与数据库兼容"""
    print("\n=== 测试3: 数据库兼容性验证 ===")
    
    # 模拟数据库场景：TIMESTAMP WITHOUT TIME ZONE
    quiz_output = QuizGenerationOutput(
        concept_id="test-concept",
        quiz_id="test-quiz-id",
        questions=[
            QuizQuestion(
                question_id="q1",
                question_type="single_choice",
                question="测试题目",
                options=["A", "B", "C"],
                correct_answer=[0],  # 正确答案索引列表
                explanation="测试解析",
                difficulty="easy",
            )
        ],
        total_questions=1,
    )
    
    # 通过 _ensure_naive_datetime 处理
    safe_created_at = _ensure_naive_datetime(quiz_output.created_at)
    
    print(f"✅ 原始 created_at: {quiz_output.created_at}, tzinfo={quiz_output.created_at.tzinfo}")
    print(f"✅ 安全处理后: {safe_created_at}, tzinfo={safe_created_at.tzinfo}")
    
    # 验证可以用于数据库插入（不会报错）
    assert safe_created_at.tzinfo is None, "数据库兼容性要求无时区信息"
    print("✅ 通过: datetime可安全用于TIMESTAMP WITHOUT TIME ZONE字段")
    
    return True


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Datetime 时区修复验证")
    print("=" * 60)
    
    all_passed = True
    
    try:
        test1_passed = test_quiz_output_created_at()
        all_passed = all_passed and test1_passed
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        all_passed = False
    
    try:
        test2_passed = test_ensure_naive_datetime()
        all_passed = all_passed and test2_passed
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
        all_passed = False
    
    try:
        test3_passed = test_database_compatibility()
        all_passed = all_passed and test3_passed
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！datetime时区问题已修复")
    else:
        print("❌ 部分测试失败，请检查修复")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
