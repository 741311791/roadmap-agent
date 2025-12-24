#!/bin/bash
# CORS 诊断脚本

set -e

echo "🔍 CORS 跨域问题诊断工具"
echo "================================"
echo ""

BACKEND_URL="https://roadmap-agent-production.up.railway.app"
FRONTEND_ORIGIN="https://www.fastlearning.app"

# 测试 1: 健康检查
echo "📋 测试 1: 后端健康检查"
echo "------------------------"
HEALTH_RESPONSE=$(curl -s "$BACKEND_URL/health")
echo "响应: $HEALTH_RESPONSE"
if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
  echo "✅ 后端服务运行正常"
else
  echo "❌ 后端服务可能有问题"
fi
echo ""

# 测试 2: OPTIONS 预检请求
echo "📋 测试 2: CORS 预检请求 (OPTIONS)"
echo "------------------------"
echo "请求: OPTIONS $BACKEND_URL/api/v1/auth/jwt/login"
echo "Origin: $FRONTEND_ORIGIN"
echo ""

CORS_RESPONSE=$(curl -X OPTIONS \
  "$BACKEND_URL/api/v1/auth/jwt/login" \
  -H "Origin: $FRONTEND_ORIGIN" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  -s -D - -o /dev/null)

echo "$CORS_RESPONSE"
echo ""

# 检查关键响应头
if echo "$CORS_RESPONSE" | grep -qi "access-control-allow-origin"; then
  ALLOW_ORIGIN=$(echo "$CORS_RESPONSE" | grep -i "access-control-allow-origin" | cut -d' ' -f2- | tr -d '\r')
  echo "🔍 Access-Control-Allow-Origin: $ALLOW_ORIGIN"
  
  if [[ "$ALLOW_ORIGIN" == "$FRONTEND_ORIGIN" ]]; then
    echo "✅ CORS Allow-Origin 配置正确"
  elif [[ "$ALLOW_ORIGIN" == "*" ]]; then
    echo "⚠️  CORS 配置为通配符 (*) - 不推荐生产环境使用"
  else
    echo "❌ CORS Allow-Origin 不匹配"
    echo "   期望: $FRONTEND_ORIGIN"
    echo "   实际: $ALLOW_ORIGIN"
  fi
else
  echo "❌ 响应中缺少 Access-Control-Allow-Origin 头"
  echo "   这意味着 CORS 中间件未生效或环境变量未配置"
fi
echo ""

if echo "$CORS_RESPONSE" | grep -qi "access-control-allow-credentials"; then
  ALLOW_CREDS=$(echo "$CORS_RESPONSE" | grep -i "access-control-allow-credentials" | cut -d' ' -f2- | tr -d '\r')
  echo "🔍 Access-Control-Allow-Credentials: $ALLOW_CREDS"
  if [[ "$ALLOW_CREDS" == "true" ]]; then
    echo "✅ CORS Allow-Credentials 配置正确"
  else
    echo "❌ CORS Allow-Credentials 应该为 true"
  fi
else
  echo "❌ 响应中缺少 Access-Control-Allow-Credentials 头"
fi
echo ""

if echo "$CORS_RESPONSE" | grep -qi "access-control-allow-methods"; then
  ALLOW_METHODS=$(echo "$CORS_RESPONSE" | grep -i "access-control-allow-methods" | cut -d' ' -f2- | tr -d '\r')
  echo "🔍 Access-Control-Allow-Methods: $ALLOW_METHODS"
  if [[ "$ALLOW_METHODS" == *"POST"* ]]; then
    echo "✅ POST 方法已允许"
  else
    echo "❌ POST 方法未在允许列表中"
  fi
else
  echo "⚠️  响应中缺少 Access-Control-Allow-Methods 头"
fi
echo ""

# 测试 3: 实际 POST 请求
echo "📋 测试 3: 实际 POST 请求"
echo "------------------------"
POST_RESPONSE=$(curl -X POST \
  "$BACKEND_URL/api/v1/auth/jwt/login" \
  -H "Origin: $FRONTEND_ORIGIN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test&password=test" \
  -s -D - -o /dev/null)

echo "$POST_RESPONSE" | head -n 10
echo ""

if echo "$POST_RESPONSE" | grep -qi "access-control-allow-origin"; then
  echo "✅ 实际请求返回了 CORS 头"
else
  echo "❌ 实际请求未返回 CORS 头"
fi
echo ""

# 诊断总结
echo "================================"
echo "📊 诊断总结"
echo "================================"
echo ""

if echo "$CORS_RESPONSE" | grep -qi "access-control-allow-origin" && \
   echo "$CORS_RESPONSE" | grep -i "access-control-allow-origin" | grep -q "$FRONTEND_ORIGIN"; then
  echo "✅ CORS 配置正确！"
  echo ""
  echo "如果前端仍然报错，请检查："
  echo "1. 浏览器是否缓存了旧的 CORS 响应（清空缓存或无痕模式测试）"
  echo "2. 前端是否使用了正确的 API URL"
  echo "3. 前端请求头是否正确（Content-Type 等）"
else
  echo "❌ CORS 配置有问题！"
  echo ""
  echo "可能的原因："
  echo "1. Railway 环境变量 CORS_ORIGINS 未配置或格式错误"
  echo "2. Railway 未部署最新代码（commit eb8ecd9）"
  echo "3. FastAPI CORS 中间件配置错误"
  echo ""
  echo "请执行以下步骤："
  echo ""
  echo "【步骤 1】在 Railway Dashboard 配置环境变量"
  echo "变量名: CORS_ORIGINS"
  echo "变量值: [\"https://www.fastlearning.app\"]"
  echo ""
  echo "【步骤 2】重新部署 Railway 服务"
  echo "在 Railway Dashboard 点击 'Deploy' 按钮"
  echo ""
  echo "【步骤 3】等待 2-3 分钟后重新运行此脚本验证"
  echo "./scripts/test_cors.sh"
fi
echo ""

# 额外信息
echo "================================"
echo "📝 额外调试信息"
echo "================================"
echo ""
echo "如需查看完整响应头，运行："
echo ""
echo "curl -X OPTIONS \\"
echo "  $BACKEND_URL/api/v1/auth/jwt/login \\"
echo "  -H \"Origin: $FRONTEND_ORIGIN\" \\"
echo "  -H \"Access-Control-Request-Method: POST\" \\"
echo "  -H \"Access-Control-Request-Headers: content-type\" \\"
echo "  -v"
echo ""
echo "查看 Railway 环境变量："
echo "1. 登录 Railway Dashboard"
echo "2. 进入项目 → 后端服务 → Variables"
echo "3. 查找 CORS_ORIGINS 变量"
echo ""

