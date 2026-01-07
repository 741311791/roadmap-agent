#!/bin/bash
# 阶段1架构验证脚本

set -e

echo "🔍 验证阶段1架构基础建设..."
echo ""

# 检查目录结构
echo "📁 检查目录结构..."
directories=(
    "app/schemas"
    "app/crud"
)

for dir in "${directories[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir 存在"
    else
        echo "  ❌ $dir 不存在"
        exit 1
    fi
done
echo ""

# 检查Schemas文件
echo "📄 检查Schemas文件..."
schemas=(
    "app/schemas/__init__.py"
    "app/schemas/common.py"
    "app/schemas/roadmap.py"
    "app/schemas/concept.py"
    "app/schemas/tutorial.py"
    "app/schemas/resource.py"
    "app/schemas/quiz.py"
    "app/schemas/mentor.py"
    "app/schemas/user.py"
    "app/schemas/progress.py"
    "app/schemas/tech_assessment.py"
)

for file in "${schemas[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file 不存在"
        exit 1
    fi
done
echo ""

# 检查CRUD文件
echo "📄 检查CRUD文件..."
cruds=(
    "app/crud/__init__.py"
    "app/crud/base.py"
    "app/crud/crud_roadmap.py"
    "app/crud/crud_concept.py"
    "app/crud/crud_tutorial.py"
    "app/crud/crud_resource.py"
    "app/crud/crud_quiz.py"
    "app/crud/crud_task.py"
    "app/crud/crud_user.py"
    "app/crud/crud_progress.py"
)

for file in "${cruds[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file 不存在"
        exit 1
    fi
done
echo ""

# 检查依赖注入文件
echo "📄 检查依赖注入文件..."
if [ -f "app/api/v1/deps.py" ]; then
    echo "  ✅ app/api/v1/deps.py"
else
    echo "  ❌ app/api/v1/deps.py 不存在"
    exit 1
fi
echo ""

# 检查Session修改
echo "📄 检查Session读写分离..."
if grep -q "get_db_readonly" app/db/session.py && grep -q "get_db_transaction" app/db/session.py; then
    echo "  ✅ Session读写分离已实现"
else
    echo "  ❌ Session读写分离未实现"
    exit 1
fi
echo ""

# 检查文档
echo "📄 检查开发规范文档..."
docs=(
    "docs/CODE_REVIEW_CHECKLIST.md"
    "docs/MIGRATION_GUIDE.md"
    "docs/20260106_阶段1_架构基础建设完成总结.md"
)

for file in "${docs[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file 不存在"
        exit 1
    fi
done
echo ""

# 统计代码行数
echo "📊 代码统计..."
schemas_lines=$(find app/schemas -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')
crud_lines=$(find app/crud -name "*.py" -exec wc -l {} + | tail -1 | awk '{print $1}')
echo "  Schemas层: $schemas_lines 行"
echo "  CRUD层: $crud_lines 行"
echo ""

echo "✅ 阶段1架构基础建设验证完成！"
echo ""
echo "📝 后续步骤："
echo "  1. 阅读 docs/CODE_REVIEW_CHECKLIST.md"
echo "  2. 阅读 docs/MIGRATION_GUIDE.md"
echo "  3. 开始迁移现有代码"
echo ""

