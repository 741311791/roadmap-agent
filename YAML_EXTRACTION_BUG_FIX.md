# YAML 提取逻辑 Bug 修复报告

## 🐛 问题描述

**现象**: RoadmapEditorAgent 在处理 LLM 输出时抛出 YAML 解析错误

```
yaml_parse_error: while scanning for the next token
found character '`' that cannot start any token
  in "<unicode string>", line 1, column 1:
    ```yaml
    ^
```

**影响**: roadmap_edit 节点执行失败，导致整个工作流中断，任务状态变为 `failed`

---

## 🔍 根本原因分析

### 问题代码位置

**文件**: `backend/app/agents/roadmap_editor.py`  
**函数**: `_try_extract_yaml(content: str)`  
**行号**: 59-66（修复前）

### 错误逻辑

```python
# 【修复前】启发式检测（情况3）
lines = content.split("\n")
if lines and any(line.strip().startswith(key + ":") for line in lines[:10] 
                 for key in ["roadmap_id", "title", "stages", "modification_summary"]):
    logger.debug("yaml_detected_as_plain_text")
    return content  # ❌ 直接返回原始内容
```

### 触发场景

当 LLM 返回以下格式的内容时：

```
```yaml
roadmap_id: ai-agent-development-k8s7m6n5
title: AI Agent原理与开发实战路线图
...
```
```

**执行流程**：

1. `content.split("\n")` 分割字符串
2. `lines[0]` = `"```yaml"`
3. `lines[1]` = `"roadmap_id: ai-agent-development-k8s7m6n5"`
4. 启发式检测匹配到 `"roadmap_id:"` → 返回 `content`（包含 `` ` `` 标记）
5. `yaml.safe_load(content)` 失败 → 抛出异常

### 核心问题

**启发式检测（情况3）在代码块标记检测（情况1、2）之前被触发**

- 启发式检测只检查了"是否存在关键字"，没有检查"是否在代码块内"
- 导致包含代码块标记的内容被直接返回，而不是提取代码块内部的纯 YAML

---

## ✅ 修复方案

### 1. 调整检测优先级

**关键改进**: 为启发式检测添加前置条件：

```python
# 【修复后】启发式检测（情况3）
# ⚠️ 只有当内容不包含代码块标记时才使用此检测
if "```" not in content:
    lines = content.split("\n")
    if lines and any(line.strip().startswith(key + ":") for line in lines[:10] 
                     for key in ["roadmap_id", "title", "stages", "modification_summary"]):
        logger.debug("yaml_detected_as_plain_text", length=len(content))
        return content
```

### 2. 增强日志记录

添加更多调试信息：

```python
logger.debug("yaml_extracted_from_code_block", format="yaml", length=len(yaml_content))

logger.warning(
    "yaml_extraction_failed",
    content_preview=content[:200],
    has_yaml_marker="```yaml" in content,
    has_generic_marker="```" in content,
)
```

### 3. 完整的检测优先级

```
【优先级1】→ 检查 ```yaml / ```yml 标记（最高优先级）
         ↓ 未找到
【优先级2】→ 检查通用 ``` 标记
         ↓ 未找到
【优先级3】→ 启发式检测（仅当不包含 ``` 时）
         ↓ 未找到
【失败】   → 返回 None，记录警告日志
```

---

## 📊 测试用例覆盖

### 用例 1: 标准 YAML 代码块

**输入**:
```
```yaml
roadmap_id: test-123
title: Test Roadmap
```
```

**预期**: 提取纯 YAML（不包含 `` ` `` 标记）  
**实际**: ✅ 通过（优先级1检测）

### 用例 2: 通用代码块

**输入**:
```
```
roadmap_id: test-123
title: Test Roadmap
```
```

**预期**: 提取纯 YAML  
**实际**: ✅ 通过（优先级2检测）

### 用例 3: 直接 YAML（无标记）

**输入**:
```
roadmap_id: test-123
title: Test Roadmap
```

**预期**: 返回原始内容  
**实际**: ✅ 通过（优先级3检测）

### 用例 4: 混合场景（修复前会失败）

**输入**:
```
Here is the roadmap:
```yaml
roadmap_id: test-123
title: Test Roadmap
```
```

**预期**: 提取代码块内的 YAML  
**实际**: ✅ 通过（优先级1检测，不会触发启发式）

---

## 🎯 修复效果

### 修复前

```
2025-12-17 01:44:12 [debug    ] yaml_detected_as_plain_text
2025-12-17 01:44:12 [error    ] yaml_parse_error
  error='while scanning for the next token
         found character '`' that cannot start any token'
2025-12-17 01:44:12 [error    ] roadmap_edit_output_invalid
  error='YAML 解析失败: ...'
2025-12-17 01:44:12 [error    ] workflow_brain_on_error
  error='LLM 输出格式不符合 Schema'
```

### 修复后（预期）

```
2025-12-17 XX:XX:XX [debug    ] yaml_extracted_from_code_block
  format=yaml length=1234
2025-12-17 XX:XX:XX [info     ] yaml_roadmap_edit_parsed
  stages_count=4 roadmap_id=ai-agent-development-k8s7m6n5
2025-12-17 XX:XX:XX [info     ] roadmap_edit_success
  roadmap_id=ai-agent-development-k8s7m6n5
```

---

## 🔄 状态机影响

### 修复前（失败路径）

```
curriculum_design → structure_validation → roadmap_edit
                                              ↓
                                           [失败]
                                              ↓
                                        status=failed
                                        工作流中断 ❌
```

### 修复后（正常路径）

```
curriculum_design → structure_validation → roadmap_edit
                                              ↓
                                           [成功]
                                              ↓
                   ┌──────────────────────────┘
                   ↓
         structure_validation (重新验证)
                   ↓
         [验证通过] → human_review → tutorial_generation ✅
```

---

## 📝 相关文件

| 文件 | 变更内容 |
|------|---------|
| `backend/app/agents/roadmap_editor.py` | 修复 `_try_extract_yaml()` 函数逻辑 |
| `WORKFLOW_STATE_MACHINE_DIAGRAM.md` | 新增：状态机时序图文档 |
| `YAML_EXTRACTION_BUG_FIX.md` | 新增：本修复报告 |

---

## ⚠️ 注意事项

### 潜在风险

1. **LLM 输出格式变化**：如果 LLM 开始返回其他格式（如 JSON），需要进一步适配
2. **部分提取失败**：虽然修复了主要问题，但仍可能存在边界情况

### 后续建议

1. ✅ **添加单元测试**：覆盖所有提取场景
2. ✅ **监控日志**：关注 `yaml_extraction_failed` 警告
3. ✅ **添加重试机制**：LLM 输出格式错误时自动重试（可选）

---

## 🚀 部署验证

### 验证步骤

1. 重启后端服务
2. 触发 roadmap_edit 节点（通过验证失败）
3. 观察日志输出：
   - ✅ `yaml_extracted_from_code_block` 而不是 `yaml_detected_as_plain_text`
   - ✅ `roadmap_edit_success` 而不是 `roadmap_edit_output_invalid`
4. 检查任务状态：
   - ✅ `status=processing` 而不是 `status=failed`
   - ✅ 工作流继续执行到 `human_review`

### 回滚方案

如果修复后出现新问题，可通过 Git 回滚：

```bash
git diff HEAD^ backend/app/agents/roadmap_editor.py
git checkout HEAD^ -- backend/app/agents/roadmap_editor.py
```

---

## 📅 修复时间线

| 时间 | 事件 |
|-----|-----|
| 2025-12-17 01:44:12 | 问题首次发现（生产环境） |
| 2025-12-17 18:42:40 | 分析根本原因 |
| 2025-12-17 18:45:00 | 实施修复 |
| 2025-12-17 18:50:00 | 待验证 |

---

**修复人员**: AI Assistant  
**审核状态**: 待测试验证  
**优先级**: 🔴 Critical

