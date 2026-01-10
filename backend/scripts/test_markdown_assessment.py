#!/usr/bin/env python3
"""
测试技术栈测验题目的 Markdown 渲染优化

功能：
- 生成包含代码的测验题目
- 检查题目中是否使用了 Markdown 代码块格式
- 输出示例题目供前端测试
"""
import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.tech_assessment_generator import TechAssessmentGenerator
import structlog

logger = structlog.get_logger()


async def test_markdown_code_blocks():
    """
    测试生成的题目是否包含 Markdown 格式的代码块
    """
    print("=" * 80)
    print("技术栈测验题目 Markdown 渲染测试")
    print("=" * 80)
    print()
    
    # 创建生成器实例
    generator = TechAssessmentGenerator()
    
    # 测试不同的技术栈和级别
    test_cases = [
        {"technology": "python", "proficiency_level": "intermediate"},
        {"technology": "javascript", "proficiency_level": "intermediate"},
    ]
    
    for test_case in test_cases:
        technology = test_case["technology"]
        proficiency_level = test_case["proficiency_level"]
        
        print(f"\n📝 生成 {technology.upper()} ({proficiency_level}) 测验题目...")
        print("-" * 80)
        
        try:
            # 生成测验题目
            result = await generator.generate_assessment_with_plan(
                technology=technology,
                proficiency_level=proficiency_level,
            )
            
            questions = result.get("questions", [])
            total_questions = len(questions)
            
            print(f"✅ 成功生成 {total_questions} 道题目\n")
            
            # 统计包含代码块的题目
            markdown_code_count = 0
            inline_code_count = 0
            plain_code_count = 0
            
            for i, q in enumerate(questions, 1):
                question_text = q.get("question", "")
                
                # 检查是否包含 Markdown 代码块（三反引号）
                has_markdown_code = "```" in question_text
                # 检查是否包含行内代码（单反引号）
                has_inline_code = "`" in question_text and not has_markdown_code
                # 检查是否包含未格式化的代码（包含常见代码关键字但无反引号）
                has_plain_code = (
                    any(keyword in question_text.lower() for keyword in [
                        "def ", "class ", "import ", "from ", "function ", 
                        "const ", "let ", "var ", "=>", "SELECT ", "WHERE "
                    ]) and "`" not in question_text
                )
                
                if has_markdown_code:
                    markdown_code_count += 1
                    print(f"\n✅ 题目 #{i} - 包含 Markdown 代码块")
                    print(f"   类型: {q.get('type')}")
                    print(f"   题目预览:")
                    # 只显示前300个字符
                    preview = question_text[:300]
                    if len(question_text) > 300:
                        preview += "..."
                    print(f"   {preview}")
                    
                elif has_inline_code:
                    inline_code_count += 1
                    print(f"\n📝 题目 #{i} - 包含行内代码")
                    print(f"   类型: {q.get('type')}")
                    
                elif has_plain_code:
                    plain_code_count += 1
                    print(f"\n⚠️ 题目 #{i} - 包含未格式化的代码（需要优化）")
                    print(f"   类型: {q.get('type')}")
                    print(f"   题目: {question_text[:200]}...")
                    
                # 检查选项中是否包含代码
                options = q.get("options", [])
                for opt_idx, opt in enumerate(options, 1):
                    if "```" in opt:
                        print(f"   ✅ 选项 {opt_idx} 也包含 Markdown 代码块")
            
            # 输出统计结果
            print("\n" + "=" * 80)
            print(f"📊 统计结果 ({technology.upper()}):")
            print(f"   总题目数: {total_questions}")
            print(f"   包含 Markdown 代码块: {markdown_code_count} 道")
            print(f"   包含行内代码: {inline_code_count} 道")
            print(f"   包含未格式化代码: {plain_code_count} 道")
            print(f"   纯文本题目: {total_questions - markdown_code_count - inline_code_count - plain_code_count} 道")
            
            if markdown_code_count > 0:
                print(f"\n✅ 成功：已有 {markdown_code_count} 道题目使用 Markdown 格式")
            if plain_code_count > 0:
                print(f"\n⚠️ 警告：还有 {plain_code_count} 道题目包含未格式化的代码，需要 LLM 优化")
            
            # 保存完整结果到文件，供前端测试
            output_file = f"test_assessment_{technology}_{proficiency_level}.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n💾 完整结果已保存到: {output_file}")
            
        except Exception as e:
            print(f"❌ 生成失败: {str(e)}")
            logger.error("test_failed", error=str(e), error_type=type(e).__name__)
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


async def main():
    """主函数"""
    try:
        await test_markdown_code_blocks()
    except KeyboardInterrupt:
        print("\n\n⚠️ 测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试失败: {str(e)}")
        logger.error("main_failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())

