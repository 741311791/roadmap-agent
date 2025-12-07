#!/usr/bin/env python3
"""
批量修复所有 Agent 提示词模板，确保 JSON 输出指令清晰
"""
import re
from pathlib import Path

# 需要修复的 JSON 格式提示词文件
JSON_PROMPT_FILES = [
    "modification_analyzer.j2",
    "quiz_generator.j2", 
    "quiz_modifier.j2",
    "resource_modifier.j2",
    "resource_recommender.j2",
    "roadmap_editor.j2",
    "structure_validator.j2",
    "tutorial_generator.j2",
]

JSON_FORMAT_INSTRUCTION = """
**重要：请直接返回纯 JSON 对象，不要使用 markdown 代码块包裹（不要使用 ```json 或 ```）**
"""

def fix_prompt_file(file_path: Path):
    """修复单个提示词文件"""
    content = file_path.read_text(encoding='utf-8')
    
    # 检查是否已包含指令
    if "不要使用 markdown 代码块包裹" in content or "不要使用 ```json" in content:
        print(f"✓ {file_path.name} - Already fixed")
        return False
    
    # 查找 [4. Output Format] 或类似的部分
    pattern = r'(\[4\. Output Format\])'
    match = re.search(pattern, content)
    
    if match:
        # 在 Output Format 标题后插入指令
        insert_pos = match.end()
        new_content = (
            content[:insert_pos] + 
            "\n" + JSON_FORMAT_INSTRUCTION.strip() + "\n" +
            content[insert_pos:]
        )
        file_path.write_text(new_content, encoding='utf-8')
        print(f"✓ {file_path.name} - Fixed")
        return True
    else:
        print(f"⚠ {file_path.name} - No [4. Output Format] section found")
        return False

def main():
    prompts_dir = Path(__file__).parent.parent / "prompts"
    print(f"Fixing JSON prompt templates in: {prompts_dir}\n")
    
    fixed_count = 0
    for filename in JSON_PROMPT_FILES:
        file_path = prompts_dir / filename
        if file_path.exists():
            if fix_prompt_file(file_path):
                fixed_count += 1
        else:
            print(f"✗ {filename} - File not found")
    
    print(f"\n✓ Fixed {fixed_count} prompt files")

if __name__ == "__main__":
    main()

