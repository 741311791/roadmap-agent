#!/usr/bin/env python3
"""
批量修复所有 Agent 的 __init__ 方法

所有 Agent 都需要接受参数以支持 Factory 模式，
同时保持向后兼容（支持无参数实例化）。
"""

import re
from pathlib import Path

# Agent 配置映射（agent_file -> settings_prefix）
AGENT_CONFIGS = {
    "curriculum_architect.py": "ARCHITECT",
    "modification_analyzer.py": "MODIFICATION_ANALYZER",
    "quiz_generator.py": "QUIZ",
    "quiz_modifier.py": "QUIZ_MODIFIER",
    "resource_modifier.py": "RESOURCE_MODIFIER",
    "resource_recommender.py": "RECOMMENDER",
    "roadmap_editor.py": "EDITOR",
    "structure_validator.py": "VALIDATOR",
    "tutorial_generator.py": "GENERATOR",
    "tutorial_modifier.py": "TUTORIAL_MODIFIER",
}

def fix_agent_init(file_path: Path, settings_prefix: str):
    """修复单个 Agent 文件"""
    
    content = file_path.read_text()
    
    # 查找旧的 __init__ 方法
    old_init_pattern = r'def __init__\(self\):\s+super\(\).__init__\(\s+agent_id="([^"]+)",\s+model_provider=settings\.(\w+)_PROVIDER,\s+model_name=settings\.(\w+)_MODEL,\s+base_url=settings\.(\w+)_BASE_URL,\s+api_key=settings\.(\w+)_API_KEY,'
    
    match = re.search(old_init_pattern, content, re.MULTILINE | re.DOTALL)
    
    if not match:
        print(f"⚠️  {file_path.name}: 未找到匹配的 __init__ 模式，可能已修复或格式不同")
        return False
    
    agent_id = match.group(1)
    
    # 新的 __init__ 方法
    new_init = f'''def __init__(
        self,
        agent_id: str = "{agent_id}",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.{settings_prefix}_PROVIDER,
            model_name=model_name or settings.{settings_prefix}_MODEL,
            base_url=base_url or settings.{settings_prefix}_BASE_URL,
            api_key=api_key or settings.{settings_prefix}_API_KEY,'''
    
    # 替换
    content_new = re.sub(
        r'def __init__\(self\):\s+super\(\).__init__\(',
        new_init.replace('(', r'\(').replace(')', r'\)') + '(',
        content,
        count=1
    )
    
    if content_new != content:
        file_path.write_text(content_new)
        print(f"✅ {file_path.name}: 已修复")
        return True
    else:
        print(f"❌ {file_path.name}: 替换失败")
        return False


def main():
    """主函数"""
    agents_dir = Path("backend/app/agents")
    
    if not agents_dir.exists():
        print(f"❌ 目录不存在: {agents_dir}")
        return
    
    print("开始修复 Agent __init__ 方法...")
    print("=" * 60)
    
    fixed_count = 0
    skipped_count = 0
    
    for agent_file, settings_prefix in AGENT_CONFIGS.items():
        file_path = agents_dir / agent_file
        
        if not file_path.exists():
            print(f"⚠️  文件不存在: {agent_file}")
            skipped_count += 1
            continue
        
        if fix_agent_init(file_path, settings_prefix):
            fixed_count += 1
        else:
            skipped_count += 1
    
    print("=" * 60)
    print(f"修复完成: {fixed_count} 个成功, {skipped_count} 个跳过")
    print()
    print("注意: intent_analyzer.py 已手动修复，未包含在此脚本中")


if __name__ == "__main__":
    main()

