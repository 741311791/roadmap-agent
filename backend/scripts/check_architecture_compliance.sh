#!/bin/bash
# 架构合规性检查工具

echo "=================================="
echo "  架构合规性检查工具"
echo "=================================="

violations=0
total_files=0

# 检查API层是否直接调用Repository/CRUD
for file in app/api/v1/endpoints/*.py; do
    if [[ "$file" == *"__init__.py" ]] || [[ "$file" == *"deps.py" ]]; then
        continue
    fi
    
    total_files=$((total_files + 1))
    filename=$(basename "$file")
    
    # 检查Repository实例化
    repo_count=$(grep -c "Repository(" "$file" 2>/dev/null || echo "0")
    # 检查CRUD实例化
    crud_count=$(grep -c "CRUD(" "$file" 2>/dev/null || echo "0")
    
    total_violations=$((repo_count + crud_count))
    
    if [ $total_violations -gt 0 ]; then
        echo "❌ $filename: $total_violations 个违规"
        violations=$((violations + total_violations))
    else
        echo "✅ $filename: 0个违规"
    fi
done

echo ""
echo "=================================="
echo "  检查结果"
echo "=================================="
echo "总文件数: $total_files"
echo "违规总数: $violations"

if [ $violations -eq 0 ]; then
    echo "✅ 架构合规性检查通过！"
    exit 0
else
    echo "❌ 发现违规，请修复"
    exit 1
fi
