#!/bin/bash
# 阶段0修复验证脚本

set -e

echo "========================================"
echo "阶段0：紧急止血修复 - 验证测试"
echo "========================================"
echo ""

BASE_URL="${BASE_URL:-http://localhost:8000}"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 测试结果统计
PASS=0
FAIL=0

# 测试函数
test_endpoint() {
    local name="$1"
    local command="$2"
    local expected="$3"
    
    echo -n "测试: $name ... "
    
    if eval "$command" | grep -q "$expected"; then
        echo -e "${GREEN}✓ 通过${NC}"
        ((PASS++))
    else
        echo -e "${RED}✗ 失败${NC}"
        ((FAIL++))
    fi
}

echo "1️⃣  测试健康检查端点"
echo "----------------------------------------"
test_endpoint \
    "基础健康检查" \
    "curl -s $BASE_URL/health" \
    "healthy"

test_endpoint \
    "RequestID响应头（GET请求）" \
    "curl -s -D - $BASE_URL/health -o /dev/null" \
    "X-Request-ID"

echo ""
echo "2️⃣  测试CORS预检 + RequestID"
echo "----------------------------------------"
test_endpoint \
    "CORS预检请求" \
    "curl -s -X OPTIONS $BASE_URL/api/v1/health -H 'Origin: http://localhost:3000' -D - -o /dev/null" \
    "Access-Control-Allow-Origin"

test_endpoint \
    "CORS预检包含RequestID" \
    "curl -s -X OPTIONS $BASE_URL/api/v1/health -H 'Origin: http://localhost:3000' -D - -o /dev/null" \
    "X-Request-ID"

echo ""
echo "3️⃣  测试中间件顺序"
echo "----------------------------------------"
echo -n "测试: RequestID在所有响应中 ... "
request_id_1=$(curl -s -D - $BASE_URL/health -o /dev/null | grep -i "X-Request-ID" | cut -d' ' -f2 | tr -d '\r')
request_id_2=$(curl -s -D - $BASE_URL/health -o /dev/null | grep -i "X-Request-ID" | cut -d' ' -f2 | tr -d '\r')

if [[ -n "$request_id_1" && -n "$request_id_2" && "$request_id_1" != "$request_id_2" ]]; then
    echo -e "${GREEN}✓ 通过${NC} (每次请求生成唯一ID)"
    ((PASS++))
else
    echo -e "${RED}✗ 失败${NC}"
    ((FAIL++))
fi

echo ""
echo "4️⃣  测试WebSocket端点可访问性"
echo "----------------------------------------"
test_endpoint \
    "WebSocket路由存在" \
    "curl -s -o /dev/null -w '%{http_code}' $BASE_URL/api/v1/ws/test-task" \
    "400\|403\|426"  # 400/403/426 都表示端点存在但需要升级到WebSocket

echo ""
echo "5️⃣  测试认证扩展端点"
echo "----------------------------------------"
test_endpoint \
    "登出端点存在" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST $BASE_URL/api/v1/auth/logout" \
    "401\|403"  # 401/403 表示端点存在但需要认证

echo ""
echo "========================================"
echo "测试完成"
echo "========================================"
echo -e "✓ 通过: ${GREEN}$PASS${NC}"
echo -e "✗ 失败: ${RED}$FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！${NC}"
    exit 0
else
    echo -e "${RED}⚠️  有 $FAIL 个测试失败${NC}"
    exit 1
fi

