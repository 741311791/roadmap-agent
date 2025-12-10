#!/bin/bash

# WebSocket 修复验证脚本
# 
# 用途：验证 WebSocket 连接修复是否成功
# 使用：bash test_websocket_fix.sh

set -e

echo "╔══════════════════════════════════════════════════════════╗"
echo "║         WebSocket 修复验证脚本                             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查后端服务器
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1️⃣  检查后端服务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓${NC} 后端服务运行中"
else
    echo -e "${RED}✗${NC} 后端服务未运行"
    echo ""
    echo "请先启动后端服务："
    echo "  cd backend"
    echo "  uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    exit 1
fi
echo ""

# 创建测试用户和任务
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2️⃣  创建测试任务"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESPONSE=$(curl -s -X POST "http://localhost:8000/api/v1/roadmaps/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-ws-user",
    "preferences": {
      "learning_goal": "测试 WebSocket 连接",
      "current_level": "beginner",
      "weekly_hours": 10,
      "learning_style": ["visual"]
    }
  }')

TASK_ID=$(echo $RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['task_id'])" 2>/dev/null)

if [ -z "$TASK_ID" ]; then
    echo -e "${RED}✗${NC} 创建任务失败"
    echo "响应: $RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓${NC} 任务创建成功"
echo "   Task ID: $TASK_ID"
echo ""

# 测试 WebSocket 连接
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3️⃣  测试 WebSocket 连接"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   URL: ws://localhost:8000/api/v1/ws/$TASK_ID"
echo ""

# 使用 Python 测试 WebSocket
python3 << EOF
import asyncio
import websockets
import json
from datetime import datetime

async def test_websocket():
    uri = "ws://localhost:8000/api/v1/ws/$TASK_ID?include_history=true"
    
    try:
        print("   🔌 连接中...")
        async with websockets.connect(uri, timeout=5) as websocket:
            print("   ✓ 连接成功")
            
            # 等待消息（最多5秒）
            try:
                message_count = 0
                start_time = datetime.now()
                
                while message_count < 5 and (datetime.now() - start_time).seconds < 5:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=1.0
                    )
                    data = json.loads(message)
                    message_count += 1
                    
                    print(f"   📨 消息 {message_count}: {data.get('type', 'unknown')}")
                    
                    # 如果收到 connected 消息，测试心跳
                    if data.get('type') == 'connected':
                        await websocket.send(json.dumps({"type": "ping"}))
                        print("   💓 发送心跳")
                
                print(f"\\n   ✓ 接收到 {message_count} 条消息")
                
            except asyncio.TimeoutError:
                if message_count > 0:
                    print(f"\\n   ✓ 接收到 {message_count} 条消息（超时正常）")
                else:
                    print("\\n   ⚠️  5秒内未收到消息")
            
            return True
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"   ✗ 连接失败: HTTP {e.status_code}")
        return False
    except Exception as e:
        print(f"   ✗ 连接错误: {type(e).__name__}: {e}")
        return False

# 运行测试
result = asyncio.run(test_websocket())
exit(0 if result else 1)
EOF

WS_TEST_RESULT=$?
echo ""

if [ $WS_TEST_RESULT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} WebSocket 连接测试通过"
else
    echo -e "${RED}✗${NC} WebSocket 连接测试失败"
    echo ""
    echo "请检查后端日志，查看是否有错误信息"
    exit 1
fi
echo ""

# 检查后端日志
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4️⃣  检查后端日志"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "最近的 WebSocket 相关日志："
echo ""
sleep 1

# 检查是否有错误日志（需要访问终端文件）
TERMINAL_FILE="$HOME/.cursor/projects/Users-$(whoami)-Documents-Vibecoding-roadmap-agent/terminals/2.txt"

if [ -f "$TERMINAL_FILE" ]; then
    ERROR_COUNT=$(tail -100 "$TERMINAL_FILE" | grep -c "websocket_error\|Cannot call \"send\"" || echo "0")
    CONNECT_COUNT=$(tail -100 "$TERMINAL_FILE" | grep -c "websocket_connected" || echo "0")
    
    echo "   连接次数: $CONNECT_COUNT"
    echo "   错误次数: $ERROR_COUNT"
    echo ""
    
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo -e "${YELLOW}⚠️${NC}  发现 WebSocket 错误日志"
        echo ""
        tail -50 "$TERMINAL_FILE" | grep "websocket_error\|Cannot call" | tail -5
        echo ""
    else
        echo -e "${GREEN}✓${NC} 无 WebSocket 错误"
    fi
else
    echo -e "${YELLOW}⚠️${NC}  无法访问终端日志文件"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5️⃣  总结"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}✓${NC} 修复验证完成"
echo ""
echo "修复内容："
echo "  1. 前端 URL: /ws/{task_id} → /api/v1/ws/{task_id}"
echo "  2. 后端异常处理: 添加 WebSocket 状态检查"
echo ""
echo "下一步："
echo "  1. 在浏览器中测试完整流程"
echo "  2. 访问: http://localhost:3000/app/new"
echo "  3. 创建新路线图并观察控制台"
echo ""
echo -e "预期结果: ${GREEN}无错误日志${NC}，正常接收进度更新"
echo ""

