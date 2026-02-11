#!/usr/bin/env bash
#
# 前后端自动同步脚本
#
# 功能：
# 1. 检测后端 Schema 变更
# 2. 自动生成前端 TypeScript 类型
# 3. 验证 API 路由完整性
# 4. 生成变更报告
#
# 使用方式：
#   ./scripts/sync-frontend-backend.sh          # 完整同步
#   ./scripts/sync-frontend-backend.sh --check  # 仅检查变更
#   ./scripts/sync-frontend-backend.sh --force  # 强制重新生成

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
OPENAPI_ENDPOINT="${BACKEND_URL}/openapi.json"
FRONTEND_DIR="frontend-next"
CACHE_FILE="${FRONTEND_DIR}/.openapi-cache.json"
BACKUP_FILE="${FRONTEND_DIR}/.openapi-cache.backup.json"
REPORT_FILE="${FRONTEND_DIR}/.sync-report.md"

# 模式标志
CHECK_ONLY=false
FORCE_REGENERATE=false

# 解析参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --check)
            CHECK_ONLY=true
            shift
            ;;
        --force)
            FORCE_REGENERATE=true
            shift
            ;;
        *)
            echo -e "${RED}❌ 未知参数: $1${NC}"
            exit 1
            ;;
    esac
done

# ============================================================
# 辅助函数
# ============================================================

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查后端是否运行
check_backend() {
    log_info "检查后端服务..."
    
    if ! curl -f -s "${BACKEND_URL}/health" > /dev/null; then
        log_error "后端服务未运行: ${BACKEND_URL}"
        log_info "请先启动后端服务: cd backend && uvicorn app.main:app --reload"
        exit 1
    fi
    
    log_success "后端服务运行中"
}

# 获取当前 OpenAPI Schema
fetch_openapi_schema() {
    log_info "获取 OpenAPI Schema..."
    
    if ! curl -f -s "${OPENAPI_ENDPOINT}" -o /tmp/openapi-new.json; then
        log_error "无法获取 OpenAPI Schema"
        exit 1
    fi
    
    log_success "Schema 获取成功"
}

# 计算 Schema 哈希值
calculate_hash() {
    local file=$1
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        shasum -a 256 "$file" | awk '{print $1}'
    else
        # Linux
        sha256sum "$file" | awk '{print $1}'
    fi
}

# 检测 Schema 变更
detect_changes() {
    log_info "检测 Schema 变更..."
    
    if [ ! -f "$CACHE_FILE" ]; then
        log_warning "未找到缓存文件，将执行首次同步"
        return 0
    fi
    
    # 备份当前缓存
    cp "$CACHE_FILE" "$BACKUP_FILE"
    
    # 计算哈希
    OLD_HASH=$(calculate_hash "$CACHE_FILE")
    NEW_HASH=$(calculate_hash "/tmp/openapi-new.json")
    
    if [ "$OLD_HASH" = "$NEW_HASH" ]; then
        log_success "Schema 无变更"
        return 1
    fi
    
    log_warning "检测到 Schema 变更"
    
    # 生成详细变更报告
    generate_change_report
    
    return 0
}

# 生成变更报告
generate_change_report() {
    log_info "生成变更报告..."
    
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    cat > "$REPORT_FILE" <<EOF
# Frontend-Backend Sync Report

**生成时间**: ${timestamp}

## Schema 变更检测

- ✅ 检测到后端 Schema 变更
- 🔄 需要重新生成前端类型

## 变更详情

EOF
    
    # 使用 jq 比对变更（如果已安装）
    if command -v jq &> /dev/null; then
        log_info "分析 API 端点变更..."
        
        # 提取端点路径
        OLD_PATHS=$(jq -r '.paths | keys[]' "$CACHE_FILE" 2>/dev/null | sort || echo "")
        NEW_PATHS=$(jq -r '.paths | keys[]' "/tmp/openapi-new.json" | sort)
        
        # 新增的端点
        ADDED_PATHS=$(comm -13 <(echo "$OLD_PATHS") <(echo "$NEW_PATHS"))
        if [ -n "$ADDED_PATHS" ]; then
            echo "### 🆕 新增 API 端点" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
            echo '```' >> "$REPORT_FILE"
            echo "$ADDED_PATHS" >> "$REPORT_FILE"
            echo '```' >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
        fi
        
        # 删除的端点
        REMOVED_PATHS=$(comm -23 <(echo "$OLD_PATHS") <(echo "$NEW_PATHS"))
        if [ -n "$REMOVED_PATHS" ]; then
            echo "### ⚠️ 移除 API 端点" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
            echo '```' >> "$REPORT_FILE"
            echo "$REMOVED_PATHS" >> "$REPORT_FILE"
            echo '```' >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
        fi
        
        # 提取 Schema 定义
        OLD_SCHEMAS=$(jq -r '.components.schemas | keys[]' "$CACHE_FILE" 2>/dev/null | sort || echo "")
        NEW_SCHEMAS=$(jq -r '.components.schemas | keys[]' "/tmp/openapi-new.json" | sort)
        
        # 新增的 Schema
        ADDED_SCHEMAS=$(comm -13 <(echo "$OLD_SCHEMAS") <(echo "$NEW_SCHEMAS"))
        if [ -n "$ADDED_SCHEMAS" ]; then
            echo "### 🆕 新增 Schema 定义" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
            echo '```' >> "$REPORT_FILE"
            echo "$ADDED_SCHEMAS" >> "$REPORT_FILE"
            echo '```' >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
        fi
        
        # 删除的 Schema
        REMOVED_SCHEMAS=$(comm -23 <(echo "$OLD_SCHEMAS") <(echo "$NEW_SCHEMAS"))
        if [ -n "$REMOVED_SCHEMAS" ]; then
            echo "### ⚠️ 移除 Schema 定义" >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
            echo '```' >> "$REPORT_FILE"
            echo "$REMOVED_SCHEMAS" >> "$REPORT_FILE"
            echo '```' >> "$REPORT_FILE"
            echo "" >> "$REPORT_FILE"
        fi
        
        log_success "变更报告已生成: ${REPORT_FILE}"
    else
        log_warning "未安装 jq，跳过详细变更分析"
        echo "安装 jq 以获得详细的变更分析：brew install jq" >> "$REPORT_FILE"
    fi
}

# 生成前端类型
generate_types() {
    log_info "生成前端 TypeScript 类型..."
    
    # 更新缓存
    mv /tmp/openapi-new.json "$CACHE_FILE"
    
    # 运行类型生成脚本
    cd "$FRONTEND_DIR"
    
    if npm run generate:types; then
        log_success "前端类型生成成功"
        cd ..
        return 0
    else
        log_error "前端类型生成失败"
        
        # 恢复备份
        if [ -f "$BACKUP_FILE" ]; then
            log_warning "恢复缓存备份..."
            mv "$BACKUP_FILE" "$CACHE_FILE"
        fi
        
        cd ..
        return 1
    fi
}

# 验证生成的类型
validate_types() {
    log_info "验证生成的类型..."
    
    cd "$FRONTEND_DIR"
    
    if npm run type-check; then
        log_success "类型验证通过"
        cd ..
        return 0
    else
        log_error "类型验证失败"
        cd ..
        return 1
    fi
}

# 清理临时文件
cleanup() {
    log_info "清理临时文件..."
    rm -f /tmp/openapi-new.json
    rm -f "$BACKUP_FILE"
    log_success "清理完成"
}

# ============================================================
# 主流程
# ============================================================

main() {
    echo ""
    echo "╔════════════════════════════════════════════════╗"
    echo "║   Frontend-Backend Schema Sync Tool            ║"
    echo "╚════════════════════════════════════════════════╝"
    echo ""
    
    # 1. 检查后端服务
    check_backend
    
    # 2. 获取最新 Schema
    fetch_openapi_schema
    
    # 3. 检测变更
    if [ "$FORCE_REGENERATE" = true ]; then
        log_warning "强制重新生成模式"
        HAS_CHANGES=true
    else
        if detect_changes; then
            HAS_CHANGES=true
        else
            HAS_CHANGES=false
        fi
    fi
    
    # 4. 仅检查模式
    if [ "$CHECK_ONLY" = true ]; then
        if [ "$HAS_CHANGES" = true ]; then
            log_warning "检测到变更，需要运行同步"
            cat "$REPORT_FILE" 2>/dev/null || true
            exit 1
        else
            log_success "前后端 Schema 同步"
            exit 0
        fi
    fi
    
    # 5. 生成类型（如果有变更）
    if [ "$HAS_CHANGES" = true ]; then
        if generate_types; then
            log_success "类型生成完成"
        else
            log_error "类型生成失败"
            cleanup
            exit 1
        fi
        
        # 6. 验证类型
        if validate_types; then
            log_success "类型验证通过"
        else
            log_warning "类型验证失败，请手动检查"
        fi
        
        # 7. 显示变更报告
        if [ -f "$REPORT_FILE" ]; then
            echo ""
            log_info "变更摘要:"
            echo ""
            cat "$REPORT_FILE"
        fi
    fi
    
    # 8. 清理
    cleanup
    
    echo ""
    log_success "前后端同步完成！"
    echo ""
}

# 捕获错误并清理
trap cleanup EXIT

# 执行主流程
main

