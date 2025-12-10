#!/bin/bash
# 快速测试脚本 - 验证路线图生成修复

echo "================================"
echo "路线图生成修复验证测试"
echo "================================"
echo ""

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查后端是否运行
echo "1. 检查后端服务..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 后端服务运行正常"
else
    echo -e "${RED}✗${NC} 后端服务未启动"
    echo "   请运行: cd backend && uvicorn app.main:app --reload"
    exit 1
fi

# 检查数据库连接
echo ""
echo "2. 检查数据库连接..."
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}✓${NC} 数据库连接正常"
else
    echo -e "${YELLOW}⚠${NC} 数据库状态未知"
fi

# 测试路线图生成 API
echo ""
echo "3. 测试路线图生成 API..."

# 准备测试数据
TEST_REQUEST=$(cat <<EOF
{
  "user_id": "test-user-$(date +%s)",
  "session_id": "test-session-$(date +%s)",
  "preferences": {
    "learning_goal": "学习 Python Web 开发，掌握 FastAPI 框架",
    "available_hours_per_week": 10,
    "motivation": "职业发展",
    "current_level": "intermediate",
    "career_background": "后端开发 2 年经验",
    "content_preference": ["text", "hands_on"],
    "preferred_language": "zh"
  }
}
EOF
)

echo "发起生成请求..."
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/generation/roadmap \
  -H "Content-Type: application/json" \
  -d "$TEST_REQUEST")

# 解析响应
TASK_ID=$(echo "$RESPONSE" | grep -o '"task_id":"[^"]*"' | cut -d'"' -f4)

if [ -n "$TASK_ID" ]; then
    echo -e "${GREEN}✓${NC} 生成任务已创建"
    echo "   Task ID: $TASK_ID"
    
    # 监听任务状态
    echo ""
    echo "4. 监听任务进度..."
    echo "   (按 Ctrl+C 停止监听)"
    echo ""
    
    COUNTER=0
    MAX_CHECKS=60  # 最多检查 60 次（5 分钟）
    
    while [ $COUNTER -lt $MAX_CHECKS ]; do
        STATUS_RESPONSE=$(curl -s "http://localhost:8000/api/v1/generation/task/$TASK_ID")
        
        STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        STEP=$(echo "$STATUS_RESPONSE" | grep -o '"current_step":"[^"]*"' | cut -d'"' -f4)
        ERROR=$(echo "$STATUS_RESPONSE" | grep -o '"error_message":"[^"]*"' | cut -d'"' -f4)
        
        if [ "$STATUS" = "completed" ]; then
            ROADMAP_ID=$(echo "$STATUS_RESPONSE" | grep -o '"roadmap_id":"[^"]*"' | cut -d'"' -f4)
            echo ""
            echo -e "${GREEN}✓ 任务完成！${NC}"
            echo "   Roadmap ID: $ROADMAP_ID"
            echo ""
            echo "访问路线图: http://localhost:3000/app/roadmap/$ROADMAP_ID"
            exit 0
        elif [ "$STATUS" = "failed" ]; then
            echo ""
            echo -e "${RED}✗ 任务失败${NC}"
            echo "   错误信息: $ERROR"
            
            # 检查是否是 JSON 解析错误
            if echo "$ERROR" | grep -q "JSON"; then
                echo ""
                echo -e "${RED}[问题未修复]${NC} 仍然存在 JSON 解析错误！"
                echo "请检查:"
                echo "  1. intent_analyzer.py 中的 JSON 提取逻辑"
                echo "  2. 提示词模板是否包含明确的输出格式指令"
            fi
            exit 1
        else
            echo -ne "\r   状态: $STATUS | 当前步骤: $STEP                    "
            sleep 5
            COUNTER=$((COUNTER + 1))
        fi
    done
    
    echo ""
    echo -e "${YELLOW}⚠${NC} 任务超时（5 分钟）"
    echo "   最后状态: $STATUS"
    echo "   最后步骤: $STEP"
    
else
    echo -e "${RED}✗${NC} 生成任务创建失败"
    echo "   响应: $RESPONSE"
    exit 1
fi

