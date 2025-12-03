"""
测试简洁格式的路线图解析
"""
import sys
from pathlib import Path

# 添加父目录到路径以便导入 app 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.agents.curriculum_architect import _parse_compact_roadmap


def test_compact_format_parsing():
    """测试简洁格式解析"""
    
    sample_content = """
===ROADMAP START===
ROADMAP_ID: python-web-dev
TITLE: Python Web开发完整学习路线
TOTAL_HOURS: 80
WEEKS: 8

Stage 1: 基础知识（掌握Python语法和Web基础概念）[30小时]
  Module 1.1: Python核心语法（学习Python编程基础）
    - Concept: 变量与数据类型（理解基本数据结构和变量声明）[2小时]
    - Concept: 控制流程（掌握条件判断和循环语句）[3小时]
    - Concept: 函数定义（学习函数的定义和调用）[3小时]
  Module 1.2: Web基础概念（了解HTTP协议和前端基础）
    - Concept: HTTP协议（理解请求响应模型和状态码）[2小时]
    - Concept: HTML基础（掌握基本的网页结构）[3小时]

Stage 2: 框架入门（学习Flask框架开发Web应用）[25小时]
  Module 2.1: Flask基础（掌握Flask核心概念）
    - Concept: 路由系统（理解URL映射和视图函数）[3小时]
    - Concept: 模板引擎（学习Jinja2模板语法）[4小时]
  Module 2.2: 数据库操作（学习SQLAlchemy ORM）
    - Concept: 模型定义（创建数据库模型）[4小时]
    - Concept: 查询操作（掌握CRUD操作）[5小时]

Stage 3: 综合项目实战（完成真实Web应用开发）[25小时]
  Module 3.1: 项目开发（构建完整Web应用）
    - Concept: 项目架构设计（规划项目结构）[5小时]
    - Concept: API开发（实现RESTful接口）[8小时]
    - Concept: 部署上线（将应用部署到服务器）[4小时]

DESIGN_RATIONALE: 该路线图采用渐进式设计，从Python基础到Web框架，再到实战项目，确保学习者能够系统掌握Web开发技能。
===ROADMAP END===
"""
    
    try:
        result = _parse_compact_roadmap(sample_content)
        
        print("✅ 解析成功！\n")
        print(f"📊 路线图统计:")
        print(f"  - ID: {result['framework']['roadmap_id']}")
        print(f"  - 标题: {result['framework']['title']}")
        print(f"  - 总时长: {result['framework']['total_estimated_hours']} 小时")
        print(f"  - 推荐周数: {result['framework']['recommended_completion_weeks']} 周")
        print(f"  - Stage 数量: {len(result['framework']['stages'])}")
        
        # 统计 Modules 和 Concepts
        total_modules = 0
        total_concepts = 0
        
        for stage in result['framework']['stages']:
            print(f"\n📍 {stage['name']} (Stage {stage['order']})")
            print(f"   描述: {stage['description']}")
            print(f"   模块数: {len(stage['modules'])}")
            
            total_modules += len(stage['modules'])
            
            for module in stage['modules']:
                print(f"   └─ {module['name']}")
                print(f"      概念数: {len(module['concepts'])}")
                
                total_concepts += len(module['concepts'])
                
                for concept in module['concepts']:
                    print(f"      ├─ {concept['name']} [{concept['estimated_hours']}h, {concept['difficulty']}]")
                    print(f"      │  {concept['description']}")
                    print(f"      │  关键词: {', '.join(concept['keywords'])}")
        
        print(f"\n📈 汇总统计:")
        print(f"  - 总模块数: {total_modules}")
        print(f"  - 总概念数: {total_concepts}")
        print(f"\n💡 设计说明: {result['design_rationale']}")
        
        # 验证结构完整性
        print(f"\n🔍 结构验证:")
        
        # 验证所有必需字段
        checks = []
        
        # 检查 roadmap_id
        checks.append(("roadmap_id存在", result['framework'].get('roadmap_id') is not None))
        
        # 检查每个 stage 的字段
        for stage in result['framework']['stages']:
            checks.append((f"Stage {stage['order']} 有 stage_id", 'stage_id' in stage))
            checks.append((f"Stage {stage['order']} 有 modules", len(stage.get('modules', [])) > 0))
            
            for module in stage.get('modules', []):
                checks.append((f"Module {module['module_id']} 有 concepts", len(module.get('concepts', [])) > 0))
                
                for concept in module.get('concepts', []):
                    checks.append((f"Concept {concept['concept_id']} 有完整字段", 
                                   all(k in concept for k in ['name', 'description', 'estimated_hours', 
                                                               'difficulty', 'keywords', 'content_status'])))
        
        passed = sum(1 for _, result in checks if result)
        total = len(checks)
        
        print(f"  ✅ 通过检查: {passed}/{total}")
        
        if passed < total:
            print(f"\n  ⚠️ 失败的检查:")
            for check_name, check_result in checks:
                if not check_result:
                    print(f"    - {check_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_edge_cases():
    """测试边缘情况"""
    
    print("\n" + "="*60)
    print("🧪 测试边缘情况")
    print("="*60 + "\n")
    
    # 测试 1: 缺少标记
    print("测试 1: 缺少开始/结束标记")
    try:
        _parse_compact_roadmap("ROADMAP_ID: test\nTITLE: Test")
        print("  ❌ 应该抛出异常但没有")
    except ValueError as e:
        print(f"  ✅ 正确抛出异常: {e}")
    
    # 测试 2: 格式错误的 Stage
    print("\n测试 2: 格式错误的 Stage 行")
    try:
        content = """
===ROADMAP START===
ROADMAP_ID: test
TITLE: Test
TOTAL_HOURS: 10
WEEKS: 1

Stage 1 错误格式

DESIGN_RATIONALE: Test
===ROADMAP END===
"""
        result = _parse_compact_roadmap(content)
        print(f"  ⚠️ 解析继续，stages数量: {len(result['framework']['stages'])}")
    except Exception as e:
        print(f"  ❌ 抛出异常: {e}")
    
    print("\n✅ 边缘情况测试完成")


if __name__ == "__main__":
    print("="*60)
    print("🚀 测试简洁格式路线图解析")
    print("="*60 + "\n")
    
    success = test_compact_format_parsing()
    
    if success:
        test_edge_cases()
        print("\n" + "="*60)
        print("✅ 所有测试完成！")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ 测试失败")
        print("="*60)
        sys.exit(1)

