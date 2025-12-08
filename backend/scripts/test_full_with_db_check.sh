#!/bin/bash

# 测试脚本：验证 --full 参数是否写入教程数据

echo "================================"
echo "测试流式端点 --full 参数"
echo "================================"
echo ""

# 记录开始时间
START_TIME=$(date +"%Y-%m-%d %H:%M:%S")
echo "开始时间: $START_TIME"
echo ""

# 运行测试
echo "运行: python scripts/test_streaming.py --full"
echo ""

cd "$(dirname "$0")/.."
source .venv/bin/activate

# 运行测试并捕获输出
python scripts/test_streaming.py --full 2>&1 | tee /tmp/streaming_test_output.txt

echo ""
echo "================================"
echo "检查数据库写入"
echo "================================"
echo ""

# 检查数据库
python scripts/diagnose_db.py

echo ""
echo "================================"
echo "测试完成"
echo "================================"






















