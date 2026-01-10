#!/bin/bash
#
# 测试运行脚本
#
# 提供多种测试执行模式
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Learning Roadmap Backend Test Suite  ${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查pytest是否安装（通过uv）
if ! uv run python -c "import pytest" 2>/dev/null; then
    echo -e "${RED}错误: pytest未安装${NC}"
    echo "请运行: uv pip install pytest pytest-asyncio"
    exit 1
fi

# 切换到backend目录
cd "$(dirname "$0")/.."

# 根据参数选择测试模式
case "${1:-all}" in
    "smoke")
        echo -e "${YELLOW}运行冒烟测试（健康检查 + 认证）...${NC}"
        uv run pytest tests/e2e/test_health.py tests/integration/test_auth.py -v
        ;;
    
    "unit")
        echo -e "${YELLOW}运行单元测试...${NC}"
        uv run pytest tests/unit/ -v
        ;;
    
    "integration")
        echo -e "${YELLOW}运行集成测试...${NC}"
        uv run pytest tests/integration/ -v
        ;;
    
    "e2e")
        echo -e "${YELLOW}运行端到端测试...${NC}"
        uv run pytest tests/e2e/ -v
        ;;
    
    "fast")
        echo -e "${YELLOW}运行快速测试（跳过slow标记）...${NC}"
        uv run pytest tests/ -m "not slow" -v
        ;;
    
    "coverage")
        echo -e "${YELLOW}运行测试并生成覆盖率报告...${NC}"
        uv run pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
        echo -e "${GREEN}覆盖率报告已生成: htmlcov/index.html${NC}"
        ;;
    
    "e2e-roadmap")
        echo -e "${YELLOW}运行路线图生成E2E测试...${NC}"
        uv run pytest tests/e2e/test_roadmap_generation_flow.py -v
        ;;
    
    "e2e-content")
        echo -e "${YELLOW}运行内容生成E2E测试...${NC}"
        uv run pytest tests/e2e/test_content_generation_flow.py -v
        ;;
    
    "middleware")
        echo -e "${YELLOW}运行中间件测试...${NC}"
        uv run pytest tests/integration/test_middleware.py -v
        ;;
    
    "websocket")
        echo -e "${YELLOW}运行WebSocket测试...${NC}"
        uv run pytest tests/integration/test_websocket.py -v
        ;;
    
    "all")
        echo -e "${YELLOW}运行完整测试套件...${NC}"
        uv run pytest tests/ -v
        ;;
    
    "parallel")
        echo -e "${YELLOW}运行并行测试...${NC}"
        if ! uv run python -c "import pytest_xdist" 2>/dev/null; then
            echo -e "${RED}错误: pytest-xdist未安装${NC}"
            echo "请运行: uv pip install pytest-xdist"
            exit 1
        fi
        uv run pytest tests/ -n auto -v
        ;;
    
    "help"|"-h"|"--help")
        echo "用法: ./run_tests.sh [模式]"
        echo ""
        echo "测试模式："
        echo "  smoke        - 冒烟测试（最快，~30秒）"
        echo "  unit         - 单元测试（快速，~1分钟）"
        echo "  integration  - 集成测试（中速，~3分钟）"
        echo "  e2e          - 端到端测试（中速，~2分钟）"
        echo "  e2e-roadmap  - 路线图生成E2E测试"
        echo "  e2e-content  - 内容生成E2E测试"
        echo "  middleware   - 中间件测试"
        echo "  websocket    - WebSocket连接测试"
        echo "  fast         - 快速测试，跳过slow标记"
        echo "  coverage     - 带覆盖率报告的完整测试"
        echo "  all          - 完整测试套件（默认）"
        echo "  parallel     - 并行执行测试（需要pytest-xdist）"
        echo "  help         - 显示此帮助信息"
        echo ""
        echo "示例："
        echo "  ./run_tests.sh smoke      # 运行冒烟测试"
        echo "  ./run_tests.sh coverage   # 生成覆盖率报告"
        exit 0
        ;;
    
    *)
        echo -e "${RED}错误: 未知的测试模式 '${1}'${NC}"
        echo "运行 './run_tests.sh help' 查看帮助"
        exit 1
        ;;
esac

# 检查测试结果
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ 测试通过！${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}✗ 测试失败${NC}"
    exit 1
fi

