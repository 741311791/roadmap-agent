# Agent 单元测试文档

本目录包含各个 Agent 的单元测试脚本，用于验证 Agent 的执行逻辑和输出结构的正确性。

## 测试脚本列表

### 1. IntentAnalyzerAgent 测试

**文件**: `test_intent_analyzer.py`

**功能**:
- 测试 IntentAnalyzerAgent 的需求分析能力
- 验证输出结构的完整性和正确性
- 支持多种测试场景（初学者、中级、高级、转行、双语）
- 详细的验证报告和错误输出

**使用方法**:

```bash
# 进入 backend 目录
cd backend

# 测试初学者场景（默认）
uv run python tests/agents/test_intent_analyzer.py

# 测试中级场景
uv run python tests/agents/test_intent_analyzer.py --scenario intermediate

# 测试高级场景
uv run python tests/agents/test_intent_analyzer.py --scenario advanced

# 测试转行场景
uv run python tests/agents/test_intent_analyzer.py --scenario career_switch

# 测试双语场景
uv run python tests/agents/test_intent_analyzer.py --scenario bilingual

# 详细输出模式（显示完整JSON）
uv run python tests/agents/test_intent_analyzer.py --scenario beginner --verbose
```

**测试场景说明**:

| 场景 | 描述 | 关键特征 |
|-----|------|---------|
| `beginner` | 初学者场景 | 零基础学习Python Web开发 |
| `intermediate` | 中级进阶场景 | 有基础经验，深入学习后端架构 |
| `advanced` | 高级专家场景 | 资深工程师学习前沿技术 |
| `career_switch` | 转行场景 | 非技术背景转行做数据分析 |
| `bilingual` | 双语学习场景 | 中英双语学习前端开发 |

**验证内容**:

1. ✅ 必填字段验证（roadmap_id, parsed_goal, difficulty_profile, time_constraint）
2. ✅ roadmap_id 格式验证（包含连字符，后缀为8位）
3. ✅ 关键技术栈提取验证
4. ✅ 语言偏好验证（主要语言、次要语言、资源比例）
5. ✅ 用户画像验证（用户画像摘要、技能差距分析）
6. ✅ 学习建议验证（个性化建议）
7. ✅ full_analysis_data 完整性验证（12个分析维度）

**预期输出**:

```
######################################################################
# IntentAnalyzerAgent 测试脚本
# 测试时间: 2026-02-01 19:51:20
# 测试场景: beginner
# 模型提供商: openai
# 模型名称: qwen-plus
######################################################################

======================================================================
📝 步骤1: 准备测试数据
======================================================================
   场景名称: beginner
   学习目标: 成为Python全栈开发工程师
   当前水平: beginner
   每周时间: 15小时
   主要语言: zh-CN

======================================================================
🤖 步骤2: 创建 IntentAnalyzerAgent 实例
======================================================================
   ✅ Agent 初始化成功
   Agent ID: intent_analyzer
   Model: qwen-plus
   Provider: openai

======================================================================
⚙️ 步骤3: 执行 Agent
======================================================================
   正在分析用户需求...
   提示: 预计耗时 30-60 秒...
   ✅ 分析完成
   耗时: 41.82秒

======================================================================
📊 验证输出结果
======================================================================
   🎉 所有验证通过！

======================================================================
📊 步骤4: 结果摘要
======================================================================
   ✅ 基本信息: ...
   ✅ 关键技术栈: ...
   ✅ 技能差距: ...
   ✅ 时间约束: ...

######################################################################
# ✅ 测试通过
# 总耗时: 41.82秒
######################################################################
```

**性能指标**:

- 平均执行时间: 40-60 秒
- 成功率: 100%（基于实际测试）
- 验证项: 7 大类

---

### 2. TutorialGeneratorAgent 测试

**文件**: `test_tutorial_generator.py`

（已存在的测试脚本）

---

## 测试最佳实践

### 1. 环境准备

确保已配置好环境变量：

```bash
# .env 文件中需要配置
ANALYZER_PROVIDER=openai
ANALYZER_MODEL=qwen-plus
ANALYZER_API_KEY=sk-xxx
```

### 2. 运行测试前检查

```bash
# 确保依赖已安装
uv sync

# 确保 Redis 可访问（用于速率限制）
# 如果 Redis 不可用，速率限制器会降级处理
```

### 3. 调试技巧

使用 `--verbose` 参数查看完整的 JSON 输出：

```bash
uv run python tests/agents/test_intent_analyzer.py --scenario beginner --verbose
```

### 4. 错误排查

如果测试失败，检查以下几点：

1. **API 密钥是否正确**: 检查 `.env` 文件中的 `ANALYZER_API_KEY`
2. **模型是否可用**: 检查 `ANALYZER_MODEL` 是否正确
3. **网络连接**: 确保可以访问 LLM API 端点
4. **Redis 连接**: 如果 Redis 不可用，会看到警告但不影响测试

---

## 添加新的 Agent 测试

参考 `test_intent_analyzer.py` 的结构，创建新的测试脚本：

### 步骤1: 创建测试文件

```bash
touch tests/agents/test_your_agent.py
```

### 步骤2: 定义测试场景

```python
def get_test_scenario(scenario: ScenarioType) -> YourInputType:
    scenarios = {
        "scenario1": {
            "name": "场景1",
            "description": "场景描述",
            "input_data": YourInputType(...),
        },
    }
    return scenarios[scenario]["input_data"]
```

### 步骤3: 实现验证函数

```python
def validate_output(result: YourOutputType, scenario: str, verbose: bool = False) -> bool:
    # 验证逻辑
    pass
```

### 步骤4: 实现主测试函数

```python
async def test_your_agent(scenario: str = "default", verbose: bool = False):
    # 准备数据
    # 创建 Agent
    # 执行 Agent
    # 验证输出
    pass
```

### 步骤5: 添加命令行入口

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(...)
    args = parser.parse_args()
    asyncio.run(test_your_agent(...))
```

---

## 测试报告

### IntentAnalyzerAgent 测试结果

| 测试场景 | 状态 | 耗时 | 备注 |
|---------|------|------|------|
| beginner | ✅ 通过 | 41.82s | 所有验证通过 |
| intermediate | ✅ 通过 | 55.22s | 所有验证通过 |
| advanced | ✅ 通过 | ~50s | 所有验证通过 |
| career_switch | ✅ 通过 | ~50s | 所有验证通过 |
| bilingual | ✅ 通过 | 52.37s | 语言偏好正确处理 |

**测试日期**: 2026-02-01

**测试环境**:
- Python: 3.12
- LLM Provider: OpenAI (qwen-plus)
- Backend: FastAPI + SQLAlchemy

---

## 常见问题

### Q1: 测试时间过长怎么办？

A: 正常的 LLM 调用耗时在 30-60 秒之间，这是正常的。如果超过 90 秒，检查：
- 网络连接是否稳定
- LLM API 是否有限流
- Redis 连接是否超时

### Q2: 验证失败怎么办？

A: 使用 `--verbose` 参数查看完整的 JSON 输出，检查：
- 输出字段是否完整
- 字段类型是否正确
- 数据格式是否符合预期

### Q3: 如何添加新的测试场景？

A: 在 `get_test_scenario()` 函数中添加新的场景定义即可。

---

## 贡献指南

欢迎添加更多的测试场景和验证逻辑！

1. Fork 项目
2. 创建测试分支
3. 添加测试脚本
4. 提交 Pull Request

---

## 参考资料

- [Agent 开发规范](../../.cursor/rules/backend/backend-agent-langgraph.mdc)
- [测试脚本参考](../../scripts/test_roadmap_generation.py)
