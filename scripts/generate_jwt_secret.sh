#!/bin/bash

# ==================== JWT Secret Key 生成工具 ====================
# 用途: 为 Railway 部署生成安全的 JWT Secret Key
# 使用方法: bash scripts/generate_jwt_secret.sh

echo "🔐 正在生成 JWT Secret Key..."
echo ""

# 检查 openssl 是否可用
if ! command -v openssl &> /dev/null; then
    echo "❌ 错误: openssl 命令未找到"
    echo "   请安装 OpenSSL: brew install openssl (macOS) 或 apt-get install openssl (Linux)"
    exit 1
fi

# 生成 48 字节的随机字符串（Base64 编码后约 64 字符）
JWT_SECRET=$(openssl rand -base64 48)

echo "✅ JWT Secret Key 已生成:"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$JWT_SECRET"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 使用方法:"
echo "1. 复制上方的字符串"
echo "2. 在 Railway Dashboard 中添加环境变量:"
echo "   Key: JWT_SECRET_KEY"
echo "   Value: <粘贴上方字符串>"
echo ""
echo "⚠️  安全提醒:"
echo "   - 不要将此密钥提交到 Git 仓库"
echo "   - 不要在公开场合分享此密钥"
echo "   - 生产环境和测试环境应使用不同的密钥"
echo ""

