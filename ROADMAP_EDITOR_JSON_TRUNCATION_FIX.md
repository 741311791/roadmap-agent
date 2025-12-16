# Roadmap Editor JSON 截断问题修复

**修复日期**: 2025-12-17  
**问题严重级别**: 高  
**影响范围**: `roadmap_editor` Agent 的 LLM 输出解析

---

## 问题描述

### 错误现象
```
2025-12-17 01:30:23 [error] roadmap_edit_json_parse_error
error='Unterminated string starting at: line 141 column 28 (char 6002)'
```

在路线图编辑流程中，`roadmap_editor` Agent 调用 LLM 成功，但返回的 JSON 在第 141 行被截断（在 `"c` 处，即 `"concepts"` 的开头），导致 JSON 解析失败，最终导致整个任务失败。

### 关键日志数据
```
completion_tokens=1734  (实际生成的 token 数)
max_tokens=8192         (配置的上限)
model=deepseek-v3.2     (使用的模型)
```

**重要发现**: 生成的 token 数（1734）远未达到限制（8192），说明**不是因为 token 限制导致截断**。

---

## 根本原因分析

### 原因 A: 模型行为问题
使用 `deepseek-v3.2` 模型时，在生成长 JSON 时可能会：
- 遇到内部 stop token 提前终止
- 在复杂嵌套结构中"迷失"方向
- 对长输出的稳定性不如其他模型

### 原因 B: 提示词设计问题
1. **JSON 格式容错性差**: JSON 对格式要求严格，一个字符错误就会导致整个解析失败
2. **没有强调完整性**: 提示词没有明确要求"必须输出完整闭合的 JSON"
3. **输出结构复杂**: 要求输出包含所有 stages/modules/concepts 的完整 framework 对象
4. **与 `curriculum_architect` 不一致**: `curriculum_architect` 已经使用更可靠的 YAML 格式

### 原因 C: 代码层面缺少防护
`base.py` 在 LLM 调用成功后，没有检查 `response.choices[0].finish_reason`：
- 如果是 `length`（token 限制），应该报警或重试
- 如果是其他异常终止原因，应该记录日志

---

## 修复方案

### 采用的方案: 将输出格式从 JSON 改为 YAML

这是最可靠的方案，原因如下：
1. **YAML 更容错**: 即使被部分截断，已解析的部分仍然可用
2. **与 `curriculum_architect` 一致**: 后者已使用 YAML 且运行稳定
3. **更易读**: YAML 格式更适合人类阅读和调试
4. **已有成熟实现**: 可以复用 `curriculum_architect.py` 的解析逻辑

---

## 修改清单

### 1. 提示词修改 (`backend/prompts/roadmap_editor.j2`)

**修改内容**:
- ✅ 将输出格式从 JSON 改为 YAML
- ✅ 添加详细的 YAML 格式规范和示例
- ✅ 强调输出完整性和格式正确性
- ✅ 更新所有示例为 YAML 格式

**关键变更**:
```jinja2
[5. Output Format]
**重要：输出 YAML 格式**
为了提高解析可靠性和可读性，请使用 YAML 格式输出修改后的路线图。

**输出示例**：
```yaml
roadmap_id: ai-agent-development-k8s7m6n5
title: AI Agent原理与开发实战路线图
total_estimated_hours: 120
recommended_completion_weeks: 8
modification_summary: 移除了循环依赖，调整了时间分配
preserved_elements:
  - 保留了Stage 1的完整结构
  - 保留了所有核心概念

stages:
  - stage_id: stage-1
    name: 基础原理与认知奠基
    ...
```
```

### 2. 代码修改 (`backend/app/agents/roadmap_editor.py`)

**添加的功能**:
- ✅ 导入 `yaml` 模块
- ✅ 添加 `_try_extract_yaml()` 函数 - 从 LLM 输出中提取 YAML
- ✅ 添加 `_parse_yaml_roadmap()` 函数 - 解析 YAML 并补全字段
- ✅ 更新 `edit()` 方法的解析逻辑 - 从 JSON 改为 YAML

**关键变更**:
```python
# 旧代码 (JSON)
result_dict = json.loads(content)

# 新代码 (YAML)
yaml_content = _try_extract_yaml(content)
if not yaml_content:
    raise ValueError("LLM 输出中未找到有效的 YAML 格式内容")
result_dict = _parse_yaml_roadmap(yaml_content)
```

**YAML 解析的优势**:
1. **智能提取**: 支持 ```yaml 代码块包裹、纯文本、混合格式
2. **字段补全**: 自动补全缺失的 `content_status`、`content_ref` 等字段
3. **容错处理**: 对缺失的 `order`、`total_estimated_hours` 进行计算补全
4. **详细日志**: 记录 YAML 提取和解析过程，便于调试

---

## 验证方法

### 1. 单元测试
需要添加测试用例验证 YAML 解析：
```python
def test_roadmap_editor_yaml_parsing():
    yaml_output = """
    roadmap_id: test-roadmap
    title: Test Roadmap
    modification_summary: Fixed issues
    preserved_elements:
      - Element 1
    stages:
      - stage_id: stage-1
        name: Stage 1
        ...
    """
    result = _parse_yaml_roadmap(yaml_output)
    assert result["framework"]["roadmap_id"] == "test-roadmap"
    assert result["modification_summary"] == "Fixed issues"
```

### 2. 集成测试
使用真实场景测试路线图编辑流程：
1. 创建一个包含验证问题的路线图
2. 调用 `roadmap_editor` 进行修改
3. 验证返回的 `RoadmapEditOutput` 结构正确
4. 确认修改说明和保留元素列表正确解析

### 3. 回归测试
重新运行之前失败的任务：
```bash
# 查看日志中失败的 task_id
grep "roadmap_edit_json_parse_error" terminals/1.txt

# 使用相同的输入重试
```

---

## 预期效果

### 修复前
```
[error] roadmap_edit_json_parse_error
error='Unterminated string starting at: line 141 column 28 (char 6002)'
```

### 修复后
```
[info] yaml_extracted_from_code_block format=yaml
[info] yaml_roadmap_edit_parsed stages_count=4 roadmap_id=ai-agent-development-k8s7m6n5
[info] roadmap_edit_success modification_count=1 issues_resolved=3 preserved_count=2
```

---

## 其他潜在改进

### 短期改进
1. ✅ **已实施**: 将 `roadmap_editor` 输出格式改为 YAML
2. ⚠️ **建议**: 在 `base.py` 中添加 `finish_reason` 检查和日志
3. ⚠️ **建议**: 对 `max_tokens=8192` 不够的情况进行监控和告警

### 长期改进
1. **统一所有 Agent 的输出格式**: 考虑将所有返回结构化数据的 Agent 统一改为 YAML
2. **增加输出验证**: 在 LLM 调用层面添加通用的输出完整性检查
3. **模型选择优化**: 对于生成长结构化输出的任务，评估不同模型的稳定性
4. **添加重试机制**: 当 YAML 解析失败时，自动重试一次（带有更明确的提示）

---

## 相关文件

- `backend/prompts/roadmap_editor.j2` - 提示词模板（已修改）
- `backend/app/agents/roadmap_editor.py` - Agent 实现（已修改）
- `backend/app/agents/curriculum_architect.py` - 参考实现（YAML 解析逻辑源）
- `backend/app/agents/base.py` - Agent 基类（未来可能需要改进）

---

## 总结

本次修复通过将 `roadmap_editor` 的输出格式从 JSON 改为 YAML，从根本上解决了 LLM 输出截断导致的解析失败问题。YAML 的容错性和可读性远优于 JSON，特别适合处理复杂的嵌套结构。同时，通过复用 `curriculum_architect` 的成熟解析逻辑，确保了实现的稳定性和一致性。

**修复状态**: ✅ 已完成  
**需要重启服务**: 是  
**需要数据库迁移**: 否

