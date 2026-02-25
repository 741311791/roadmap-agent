#!/bin/bash
# 清理所有 /new 路由引用的脚本

set -e

echo "🔍 查找所有 /new 路由引用..."
echo ""

# 查找所有引用
rg --files-with-matches --type tsx --type ts '/new["\s]|href="/new' frontend-next/ 2>/dev/null || true

echo ""
echo "⚠️  需要手动处理以下文件中的 /new 引用："
echo ""
echo "1. 决定新的路由路径（如 /roadmaps/new 或 /create）"
echo "2. 批量替换所有引用"
echo "3. 创建新的路由文件"
echo ""
echo "建议替换命令（示例）："
echo "  # 将 /new 替换为 /roadmaps/new"
echo "  find frontend-next -name '*.tsx' -o -name '*.ts' | xargs sed -i '' 's|href=\"/new|href=\"/roadmaps/new|g'"
echo ""
