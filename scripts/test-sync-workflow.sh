#!/usr/bin/env bash
#
# 测试前后端同步工作流
#
# 功能：
# 1. 验证所有同步脚本可执行
# 2. 测试变更检测逻辑
# 3. 验证类型生成流程
# 4. 检查 Git 集成

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 测试计数
TESTS_PASSED=0
TESTS_FAILED=0

# ============================================================
# 辅助函数
# ============================================================

log_test() {
    echo -e "${BLUE}🧪 TEST: $1${NC}"
}

log_success() {
    echo -e "${GREEN}   ✅ $1${NC}"
    ((TESTS_PASSED++))
}

log_failure() {
    echo -e "${RED}   ❌ $1${NC}"
    ((TESTS_FAILED++))
}

log_info() {
    echo -e "${BLUE}   ℹ️  $1${NC}"
}

# ============================================================
# 测试用例
# ============================================================

test_scripts_exist() {
    log_test "检查脚本文件是否存在"
    
    local scripts=(
        "scripts/sync-frontend-backend.sh"
        "frontend-next/scripts/generate-types.ts"
        "frontend-next/scripts/check-schema-sync.ts"
    )
    
    for script in "${scripts[@]}"; do
        if [ -f "$script" ]; then
            log_success "Found: $script"
        else
            log_failure "Missing: $script"
        fi
    done
}

test_scripts_executable() {
    log_test "检查脚本是否可执行"
    
    if [ -x "scripts/sync-frontend-backend.sh" ]; then
        log_success "sync-frontend-backend.sh is executable"
    else
        log_failure "sync-frontend-backend.sh is not executable"
    fi
    
    if [ -x ".husky/pre-commit" ]; then
        log_success "pre-commit hook is executable"
    else
        log_failure "pre-commit hook is not executable"
    fi
}

test_backend_health() {
    log_test "检查后端服务健康状态"
    
    if curl -f -s http://localhost:8000/health > /dev/null; then
        log_success "Backend is running"
    else
        log_failure "Backend is not running"
        log_info "Please start backend: cd backend && uvicorn app.main:app --reload"
    fi
}

test_openapi_endpoint() {
    log_test "检查 OpenAPI 端点"
    
    if curl -f -s http://localhost:8000/openapi.json > /tmp/test-openapi.json; then
        log_success "OpenAPI schema is accessible"
        
        # 验证 JSON 格式
        if jq empty /tmp/test-openapi.json 2>/dev/null; then
            log_success "OpenAPI schema is valid JSON"
        else
            log_failure "OpenAPI schema is not valid JSON"
        fi
        
        # 检查必要字段
        if jq -e '.openapi' /tmp/test-openapi.json > /dev/null 2>&1; then
            log_success "OpenAPI version field exists"
        else
            log_failure "OpenAPI version field missing"
        fi
        
        if jq -e '.paths' /tmp/test-openapi.json > /dev/null 2>&1; then
            log_success "API paths field exists"
        else
            log_failure "API paths field missing"
        fi
        
        rm -f /tmp/test-openapi.json
    else
        log_failure "Cannot access OpenAPI endpoint"
    fi
}

test_npm_scripts() {
    log_test "检查 npm scripts 配置"
    
    cd frontend-next
    
    local scripts=(
        "generate:types"
        "check:schema-sync"
        "sync:backend"
        "type-check"
    )
    
    for script in "${scripts[@]}"; do
        if npm run | grep -q "$script"; then
            log_success "npm script exists: $script"
        else
            log_failure "npm script missing: $script"
        fi
    done
    
    cd ..
}

test_type_generation() {
    log_test "测试类型生成功能"
    
    cd frontend-next
    
    # 备份现有缓存
    if [ -f ".openapi-cache.json" ]; then
        cp .openapi-cache.json .openapi-cache.backup.json
    fi
    
    # 运行类型生成
    if npm run generate:types > /tmp/generate-output.log 2>&1; then
        log_success "Type generation completed"
        
        # 检查生成的文件
        if [ -d "types/generated" ]; then
            log_success "Generated types directory exists"
        else
            log_failure "Generated types directory missing"
        fi
        
        if [ -f ".openapi-cache.json" ]; then
            log_success "OpenAPI cache file created"
        else
            log_failure "OpenAPI cache file missing"
        fi
        
        if [ -f "types/generated/.generation-stats.json" ]; then
            log_success "Generation stats file created"
        else
            log_failure "Generation stats file missing"
        fi
    else
        log_failure "Type generation failed"
        log_info "Check output: /tmp/generate-output.log"
    fi
    
    # 恢复备份
    if [ -f ".openapi-cache.backup.json" ]; then
        mv .openapi-cache.backup.json .openapi-cache.json
    fi
    
    cd ..
}

test_sync_check() {
    log_test "测试同步状态检查"
    
    cd frontend-next
    
    if npm run check:schema-sync > /tmp/sync-check-output.log 2>&1; then
        log_success "Sync check passed (types are in sync)"
    else
        # 检查是否是预期的"不同步"错误
        if grep -q "OUT OF SYNC" /tmp/sync-check-output.log; then
            log_info "Types are out of sync (expected if backend changed)"
        else
            log_failure "Sync check failed unexpectedly"
            log_info "Check output: /tmp/sync-check-output.log"
        fi
    fi
    
    cd ..
}

test_makefile_targets() {
    log_test "检查 Makefile targets"
    
    if [ -f "Makefile" ]; then
        log_success "Makefile exists"
        
        local targets=(
            "sync"
            "check-sync"
            "sync-force"
            "generate-types"
            "type-check"
        )
        
        for target in "${targets[@]}"; do
            if grep -q "^${target}:" Makefile; then
                log_success "Makefile target exists: $target"
            else
                log_failure "Makefile target missing: $target"
            fi
        done
    else
        log_failure "Makefile not found"
    fi
}

test_github_workflows() {
    log_test "检查 GitHub Actions workflows"
    
    local workflows=(
        ".github/workflows/frontend-backend-sync.yml"
        ".github/workflows/frontend-backend-sync-check.yml"
    )
    
    for workflow in "${workflows[@]}"; do
        if [ -f "$workflow" ]; then
            log_success "Workflow exists: $workflow"
        else
            log_failure "Workflow missing: $workflow"
        fi
    done
}

test_documentation() {
    log_test "检查文档完整性"
    
    local docs=(
        "doc/20260111_前后端Schema自动同步方案.md"
        "SYNC_QUICKSTART.md"
        "README_SYNC.md"
    )
    
    for doc in "${docs[@]}"; do
        if [ -f "$doc" ]; then
            log_success "Documentation exists: $doc"
        else
            log_failure "Documentation missing: $doc"
        fi
    done
}

test_gitignore() {
    log_test "检查 .gitignore 配置"
    
    cd frontend-next
    
    # 检查是否忽略了临时文件
    if [ -f ".gitignore" ]; then
        if grep -q ".sync-report.md" .gitignore; then
            log_success ".sync-report.md is ignored"
        else
            log_info ".sync-report.md should be added to .gitignore"
        fi
    else
        log_failure ".gitignore not found in frontend-next"
    fi
    
    cd ..
}

# ============================================================
# 主流程
# ============================================================

main() {
    echo ""
    echo "╔════════════════════════════════════════════════╗"
    echo "║   Frontend-Backend Sync Workflow Test         ║"
    echo "╚════════════════════════════════════════════════╝"
    echo ""
    
    # 运行所有测试
    test_scripts_exist
    echo ""
    
    test_scripts_executable
    echo ""
    
    test_backend_health
    echo ""
    
    test_openapi_endpoint
    echo ""
    
    test_npm_scripts
    echo ""
    
    test_type_generation
    echo ""
    
    test_sync_check
    echo ""
    
    test_makefile_targets
    echo ""
    
    test_github_workflows
    echo ""
    
    test_documentation
    echo ""
    
    test_gitignore
    echo ""
    
    # 显示测试结果
    echo "════════════════════════════════════════════════"
    echo ""
    echo "Test Results:"
    echo "  ✅ Passed: $TESTS_PASSED"
    echo "  ❌ Failed: $TESTS_FAILED"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}🎉 All tests passed!${NC}"
        echo ""
        exit 0
    else
        echo -e "${YELLOW}⚠️  Some tests failed. Please review the output above.${NC}"
        echo ""
        exit 1
    fi
}

# 运行测试
main

