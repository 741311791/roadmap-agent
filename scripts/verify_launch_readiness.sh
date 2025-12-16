#!/bin/bash

# 上线准备验证脚本
# 检查所有关键配置和组件是否就绪

set -e

echo "=========================================="
echo "上线准备验证脚本"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查计数器
PASSED=0
FAILED=0

# 检查函数
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. 检查后端配置
echo "1️⃣  检查后端配置..."
echo "---"

cd backend

if [ -f .env ]; then
    check_pass "找到 .env 文件"
    
    # 检查关键配置
    if grep -q "^SKIP_STRUCTURE_VALIDATION=false" .env; then
        check_pass "SKIP_STRUCTURE_VALIDATION=false (结构验证已启用)"
    else
        check_fail "SKIP_STRUCTURE_VALIDATION 未设置为 false"
    fi
    
    if grep -q "^SKIP_HUMAN_REVIEW=false" .env; then
        check_pass "SKIP_HUMAN_REVIEW=false (人工审核已启用)"
    else
        check_fail "SKIP_HUMAN_REVIEW 未设置为 false"
    fi
    
    # 检查 JWT 配置
    if grep -q "^JWT_SECRET_KEY=" .env && ! grep -q "^JWT_SECRET_KEY=$" .env; then
        check_pass "JWT_SECRET_KEY 已配置"
    else
        check_fail "JWT_SECRET_KEY 未配置或为空"
    fi
    
    # 检查 Resend API Key
    if grep -q "^RESEND_API_KEY=" .env && ! grep -q "^RESEND_API_KEY=$" .env; then
        check_pass "RESEND_API_KEY 已配置"
    else
        check_warn "RESEND_API_KEY 未配置（邮件功能将不可用）"
    fi
    
else
    check_fail "未找到 .env 文件"
fi

echo ""

# 2. 检查前端组件
echo "2️⃣  检查前端组件..."
echo "---"

cd ../frontend-next

if [ -f "components/task/human-review-card.tsx" ]; then
    check_pass "HumanReviewCard 组件存在"
else
    check_fail "HumanReviewCard 组件不存在"
fi

if [ -f "components/task/log-cards/index.tsx" ]; then
    check_pass "LogCardRouter 组件存在"
else
    check_fail "LogCardRouter 组件不存在"
fi

if [ -f "app/(app)/tasks/[taskId]/page.tsx" ]; then
    check_pass "任务详情页存在"
else
    check_fail "任务详情页不存在"
fi

echo ""

# 3. 检查后端关键文件
echo "3️⃣  检查后端关键文件..."
echo "---"

cd ../backend

if [ -f "app/core/orchestrator/node_runners/review_runner.py" ]; then
    check_pass "ReviewRunner 存在"
else
    check_fail "ReviewRunner 不存在"
fi

if [ -f "app/core/orchestrator/node_runners/validation_runner.py" ]; then
    check_pass "ValidationRunner 存在"
else
    check_fail "ValidationRunner 不存在"
fi

if [ -f "app/api/v1/endpoints/approval.py" ]; then
    check_pass "Approval API 端点存在"
else
    check_fail "Approval API 端点不存在"
fi

if [ -f "app/services/email_service.py" ]; then
    check_pass "EmailService 存在"
else
    check_warn "EmailService 不存在（邮件功能将不可用）"
fi

echo ""

# 4. 检查数据库模型
echo "4️⃣  检查数据库模型..."
echo "---"

if grep -q "class ConceptProgress" app/models/database.py; then
    check_pass "ConceptProgress 模型存在"
else
    check_fail "ConceptProgress 模型不存在"
fi

if grep -q "class WaitlistEmail" app/models/database.py; then
    check_pass "WaitlistEmail 模型存在"
else
    check_warn "WaitlistEmail 模型不存在（Waitlist 功能将不可用）"
fi

echo ""

# 5. 检查依赖
echo "5️⃣  检查依赖..."
echo "---"

if grep -q "fastapi-users" pyproject.toml; then
    check_pass "fastapi-users 已添加到依赖"
else
    check_fail "fastapi-users 未添加到依赖"
fi

if grep -q "resend" pyproject.toml; then
    check_pass "resend 已添加到依赖"
else
    check_warn "resend 未添加到依赖（邮件功能将不可用）"
fi

echo ""

# 总结
echo "=========================================="
echo "验证结果总结"
echo "=========================================="
echo ""
echo -e "${GREEN}通过: $PASSED${NC}"
echo -e "${RED}失败: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 系统已具备上线条件！${NC}"
    exit 0
else
    echo -e "${RED}✗ 发现 $FAILED 个问题，请修复后再上线${NC}"
    exit 1
fi

