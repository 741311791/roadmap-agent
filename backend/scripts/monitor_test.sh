#!/bin/bash

# 监控批量测试进度

TERMINAL_FILE="/Users/louie/.cursor/projects/Users-louie-Documents-Vibecoding-roadmap-agent/terminals/361667.txt"

echo "=========================================="
echo "测试进度监控"
echo "=========================================="
echo ""

# 统计总行数
total_lines=$(wc -l < "$TERMINAL_FILE" 2>/dev/null || echo "0")
echo "📊 日志总行数: $total_lines"

# 查找当前测试的教程
current_test=$(grep -E "\[.*\] 测试:" "$TERMINAL_FILE" 2>/dev/null | tail -1)
if [ -n "$current_test" ]; then
    echo "📝 当前测试: $current_test"
fi

# 统计成功的教程
success_count=$(grep -c "✅ 成功！" "$TERMINAL_FILE" 2>/dev/null || echo "0")
echo "✅ 已完成: $success_count 个教程"

# 统计失败的教程
fail_count=$(grep -c "❌ 失败！" "$TERMINAL_FILE" 2>/dev/null || echo "0")
echo "❌ 失败: $fail_count 个教程"

# 显示最近的迭代信息
echo ""
echo "最近的迭代信息:"
grep "react_iteration_started\|react_loop_completed\|tutorial_generation_llm_completed" "$TERMINAL_FILE" 2>/dev/null | tail -5

# 显示最后10行日志
echo ""
echo "=========================================="
echo "最新日志 (最后10行):"
echo "=========================================="
tail -10 "$TERMINAL_FILE" 2>/dev/null

# 检查是否完成
if grep -q "测试完成！" "$TERMINAL_FILE" 2>/dev/null; then
    echo ""
    echo "=========================================="
    echo "✅ 测试已完成！"
    echo "=========================================="
    
    # 显示总结
    echo ""
    grep -A 20 "测试总结" "$TERMINAL_FILE" 2>/dev/null | head -25
fi
