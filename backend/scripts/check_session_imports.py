#!/usr/bin/env python3
"""
Session导入规范检查脚本

检查规则：
1. app/api/** 禁止导入 get_celery_session
2. app/tasks/** 禁止导入 async_session_maker
3. app/services/** 禁止直接创建 Session（通过 AST 检查）

使用方法：
    cd backend
    python scripts/check_session_imports.py

返回值：
    0 - 所有检查通过
    1 - 发现违规
"""
import sys
import ast
from pathlib import Path
from typing import List


def check_file(file_path: Path) -> List[str]:
    """
    检查单个文件的Session使用规范
    
    Args:
        file_path: Python文件路径
        
    Returns:
        错误信息列表
    """
    errors = []
    
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        errors.append(f"{file_path}: 无法读取文件 - {e}")
        return errors
    
    file_str = str(file_path)
    
    # 规则1：API层禁止导入 get_celery_session
    if "/app/api/" in file_str or "\\app\\api\\" in file_str:
        if "from app.db.celery_session import" in content or \
           ("get_celery_session" in content and "import" in content):
            errors.append(f"{file_path}: API层禁止使用 get_celery_session")
    
    # 规则2：Celery任务层禁止导入 async_session_maker
    if "/app/tasks/" in file_str or "\\app\\tasks\\" in file_str:
        if "from app.db.session import async_session_maker" in content:
            errors.append(f"{file_path}: Celery任务层禁止使用 async_session_maker")
    
    # 规则3：Service层禁止自己创建Session
    if "/app/services/" in file_str or "\\app\\services\\" in file_str:
        try:
            tree = ast.parse(content, filename=str(file_path))
            for node in ast.walk(tree):
                if isinstance(node, ast.With):
                    for item in node.items:
                        if isinstance(item.context_expr, ast.Call):
                            func = item.context_expr.func
                            
                            # 检查 async_session_maker() 或 get_celery_session()
                            if isinstance(func, ast.Name):
                                if func.id in ["async_session_maker", "get_celery_session"]:
                                    errors.append(
                                        f"{file_path}:{node.lineno}: Service层禁止自己创建Session，应使用依赖注入"
                                    )
                            
                            # 检查 async_session_maker.begin()
                            elif isinstance(func, ast.Attribute):
                                if isinstance(func.value, ast.Name):
                                    if func.value.id == "async_session_maker" and func.attr == "begin":
                                        errors.append(
                                            f"{file_path}:{node.lineno}: Service层禁止自己创建Session，应使用依赖注入"
                                        )
        except SyntaxError as e:
            errors.append(f"{file_path}:{e.lineno}: 语法错误 - {e.msg}")
        except Exception as e:
            # 其他解析错误不阻止检查
            pass
    
    return errors


def main():
    """主函数"""
    root = Path("app")
    
    if not root.exists():
        print("错误：请在 backend 目录下运行此脚本")
        sys.exit(1)
    
    all_errors = []
    checked_files = 0
    
    # 收集所有Python文件
    for py_file in root.rglob("*.py"):
        # 跳过 __pycache__ 和测试文件
        if "__pycache__" in str(py_file) or "/tests/" in str(py_file):
            continue
        
        errors = check_file(py_file)
        all_errors.extend(errors)
        checked_files += 1
    
    # 输出结果
    print(f"检查了 {checked_files} 个文件")
    
    if all_errors:
        print(f"\n❌ 发现 {len(all_errors)} 个Session使用规范违规：\n")
        for error in all_errors:
            print(f"  {error}")
        print("\n请参考文档修复：doc/20260110_Session管理规范.md")
        sys.exit(1)
    else:
        print("✅ 所有文件通过Session规范检查")
        sys.exit(0)


if __name__ == "__main__":
    main()

