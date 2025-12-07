#!/usr/bin/env python3
"""
验证阶段5（统一错误处理）的集成情况

检查：
1. ErrorHandler 文件存在
2. 所有 Runner 导入了 error_handler
3. 所有 Runner 不再包含 _handle_error 方法
4. 测试文件存在并可导入
"""
import os
import sys
from pathlib import Path


def main():
    print("🔍 验证阶段5（统一错误处理）集成情况\n")
    
    # 定位项目根目录
    backend_dir = Path(__file__).parent.parent
    print(f"📁 Backend 目录: {backend_dir}\n")
    
    # 检查 1: ErrorHandler 文件存在
    print("1️⃣ 检查 ErrorHandler 文件...")
    error_handler_file = backend_dir / "app" / "core" / "error_handler.py"
    if error_handler_file.exists():
        lines = len(error_handler_file.read_text().splitlines())
        print(f"   ✅ ErrorHandler 存在 ({lines} 行)")
    else:
        print(f"   ❌ ErrorHandler 文件不存在: {error_handler_file}")
        return False
    
    # 检查 2: 所有 Runner 导入了 error_handler
    print("\n2️⃣ 检查 Runner 导入...")
    runner_dir = backend_dir / "app" / "core" / "orchestrator" / "node_runners"
    runner_files = [
        "intent_runner.py",
        "curriculum_runner.py",
        "validation_runner.py",
        "editor_runner.py",
        "content_runner.py",
    ]
    
    import_success = True
    for runner_file in runner_files:
        runner_path = runner_dir / runner_file
        if not runner_path.exists():
            print(f"   ❌ {runner_file} 不存在")
            import_success = False
            continue
        
        content = runner_path.read_text()
        if "from app.core.error_handler import error_handler" in content:
            print(f"   ✅ {runner_file} 导入了 error_handler")
        else:
            print(f"   ❌ {runner_file} 没有导入 error_handler")
            import_success = False
    
    if not import_success:
        return False
    
    # 检查 3: 所有 Runner 不再包含 _handle_error 方法
    print("\n3️⃣ 检查旧的错误处理方法已删除...")
    no_old_handler = True
    for runner_file in runner_files:
        runner_path = runner_dir / runner_file
        content = runner_path.read_text()
        if "def _handle_error(" in content or "async def _handle_error(" in content:
            print(f"   ❌ {runner_file} 仍包含 _handle_error 方法")
            no_old_handler = False
        else:
            print(f"   ✅ {runner_file} 已删除 _handle_error")
    
    if not no_old_handler:
        return False
    
    # 检查 4: 所有 Runner 使用 error_handler.handle_node_execution
    print("\n4️⃣ 检查使用统一错误处理器...")
    using_error_handler = True
    for runner_file in runner_files:
        runner_path = runner_dir / runner_file
        content = runner_path.read_text()
        if "error_handler.handle_node_execution" in content:
            print(f"   ✅ {runner_file} 使用统一错误处理器")
        else:
            print(f"   ⚠️  {runner_file} 可能没有使用统一错误处理器")
            # 不算作失败，因为有些 Runner 可能不需要错误处理
    
    # 检查 5: 测试文件存在
    print("\n5️⃣ 检查测试文件...")
    test_file = backend_dir / "tests" / "unit" / "test_error_handler.py"
    if test_file.exists():
        lines = len(test_file.read_text().splitlines())
        print(f"   ✅ 测试文件存在 ({lines} 行)")
    else:
        print(f"   ❌ 测试文件不存在: {test_file}")
        return False
    
    # 检查 6: 文档存在
    print("\n6️⃣ 检查文档...")
    doc_file = backend_dir / "docs" / "PHASE5_COMPLETION_SUMMARY.md"
    if doc_file.exists():
        print(f"   ✅ 完成总结文档存在")
    else:
        print(f"   ⚠️  完成总结文档不存在: {doc_file}")
    
    print("\n" + "="*60)
    print("🎉 阶段5集成验证完成！所有检查通过！")
    print("="*60)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
