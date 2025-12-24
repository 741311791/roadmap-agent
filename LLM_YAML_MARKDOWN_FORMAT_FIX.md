# LLM YAML 输出中 Markdown 格式导致解析失败的修复

**修复日期**: 2025-12-24  
**问题严重级别**: 高  
**影响范围**: CurriculumArchitectAgent 和 RoadmapEditorAgent 的 YAML 输出解析

---

## 🐛 问题描述

### 错误现象

后端在生成路线图架构图时失败，报错：

```
ValueError: LLM 输出格式解析失败: 无法解析路线图输出。请确保输出为有效的 YAML 或 JSON 格式。
解析错误:
  - YAML: YAML 解析失败: while scanning for the next token
found character '`' that cannot start any token
  in "<unicode string>", line 144, column 19:
                name: `useEffect` Hook 与副作用
                      ^
```

### 问题根源

LLM 在生成 YAML 格式输出时，习惯性地在技术术语或代码片段上使用 Markdown 格式标记（特别是反引号 `` ` ``），例如：

```yaml
# ❌ 错误示例：LLM 生成的内容包含 Markdown 格式
name: `useEffect` Hook 与副作用
description: 学习如何使用 `useState` 和 `useEffect` 管理状态
keywords: [`React`, `Hooks`, `状态管理`]
```

这些 Markdown 格式标记在 YAML 中是无效的 token，会导致解析器报错。

---

## 🔍 根本原因分析

### 1. Prompt 设计问题

虽然 prompt 模板明确要求输出 YAML 格式，但**没有明确禁止使用 Markdown 格式标记**。

### 2. LLM 的默认行为

LLM 在生成技术文档时，会自动使用 Markdown 格式来标记：
- 代码片段（使用反引号）
- 强调文本（使用星号或下划线）
- 技术术语（使用反引号）

这是 LLM 的训练数据和常见用法导致的，即使在 YAML 上下文中也可能出现。

### 3. 影响范围

受影响的 Agent：
- **CurriculumArchitectAgent**: 生成路线图框架时
- **RoadmapEditorAgent**: 编辑路线图时

受影响的字段：
- `name`: 阶段/模块/概念名称
- `description`: 描述性文本
- `keywords`: 关键词列表
- 任何包含技术术语的字符串字段

---

## ✅ 修复方案

### 修复策略

在 prompt 模板中**明确禁止使用 Markdown 格式**，并提供清晰的示例说明。

### 具体修改

#### 1. `backend/prompts/curriculum_architect.j2`

在 **YAML 格式规范** 部分添加：

```jinja2
**🚨 关键格式要求**：
- **禁止使用 Markdown 格式**：在 YAML 字段值中，不要使用反引号（`）、星号（*）、下划线（_）等 Markdown 标记
  - ❌ 错误示例：name: `useEffect` Hook 与副作用
  - ✅ 正确示例：name: useEffect Hook 与副作用
- **技术术语直接书写**：API、Hook、Class 等技术术语直接使用纯文本，不要添加任何格式标记
- **代码片段处理**：如果需要在描述中提及代码，直接写文本即可（如：使用 useState 管理状态）
```

#### 2. `backend/prompts/roadmap_editor.j2`

添加同样的格式要求说明。

---

## 🎯 修复效果

### 预期改进

1. **消除解析错误**: LLM 不再在 YAML 字段值中使用 Markdown 格式标记
2. **提高解析成功率**: YAML 解析器能够正确处理所有字段值
3. **保持可读性**: 技术术语仍然清晰，只是去掉了格式标记

### 示例对比

#### 修复前（会导致解析失败）

```yaml
concepts:
  - concept_id: c-2-1-1
    name: `useEffect` Hook 与副作用
    description: 学习如何使用 `useEffect` 处理 **副作用**（如数据获取、订阅等）
    keywords: [`React`, `Hooks`, `副作用`]
```

#### 修复后（正确的 YAML 格式）

```yaml
concepts:
  - concept_id: c-2-1-1
    name: useEffect Hook 与副作用
    description: 学习如何使用 useEffect 处理副作用（如数据获取、订阅等）
    keywords: [React, Hooks, 副作用]
```

---

## 📋 测试建议

### 1. 单元测试

在 `test_curriculum_architect.py` 中添加测试用例，验证解析器能够处理包含技术术语的 YAML：

```python
def test_parse_yaml_with_technical_terms():
    """测试包含技术术语的 YAML 能够正确解析"""
    yaml_content = """
roadmap_id: react-hooks-tutorial
title: React Hooks 完整指南
stages:
  - stage_id: stage-1
    name: Hooks 基础
    concepts:
      - concept_id: c-1-1-1
        name: useState Hook 状态管理
        description: 学习如何使用 useState 管理组件状态
        keywords: [React, Hooks, useState, 状态管理]
"""
    result = _parse_yaml_roadmap(yaml_content)
    assert result["framework"]["title"] == "React Hooks 完整指南"
    assert "useState" in result["framework"]["stages"][0]["concepts"][0]["name"]
```

### 2. 集成测试

创建一个包含大量技术术语的测试用例，验证完整的生成流程：

```python
@pytest.mark.asyncio
async def test_generate_roadmap_with_tech_terms():
    """测试生成包含技术术语的路线图"""
    agent = CurriculumArchitectAgent()
    
    intent_analysis = IntentAnalysisOutput(
        parsed_goal="学习 React Hooks 和现代前端开发",
        key_technologies=["React", "TypeScript", "Vite"],
        # ...
    )
    
    result = await agent.design(
        intent_analysis=intent_analysis,
        user_preferences=preferences,
        roadmap_id="test-roadmap-id"
    )
    
    # 验证输出包含技术术语但没有 Markdown 格式
    assert "React" in result.framework.title
    assert "`" not in result.framework.title  # 不应包含反引号
```

### 3. 回归测试

使用之前失败的真实案例进行测试，确保问题已解决。

---

## 🔄 相关问题

### 类似问题排查

检查其他可能生成结构化输出的 Agent：

```bash
# 搜索所有使用 YAML 输出的 prompt 模板
grep -l "YAML" backend/prompts/*.j2
```

结果：只有 `curriculum_architect.j2` 和 `roadmap_editor.j2` 使用 YAML 格式，都已修复。

### 长期解决方案

考虑在解析层添加预处理逻辑，自动清理常见的 Markdown 格式标记：

```python
def _sanitize_yaml_content(content: str) -> str:
    """
    清理 YAML 内容中的常见 Markdown 格式标记
    
    注意：这是一个回退方案，最好还是在 prompt 层面解决
    """
    # 移除反引号
    content = re.sub(r'`([^`]+)`', r'\1', content)
    
    # 移除强调标记（星号、下划线）
    content = re.sub(r'\*\*([^*]+)\*\*', r'\1', content)
    content = re.sub(r'__([^_]+)__', r'\1', content)
    content = re.sub(r'\*([^*]+)\*', r'\1', content)
    content = re.sub(r'_([^_]+)_', r'\1', content)
    
    return content
```

**建议**: 暂时不实现此方案，先观察 prompt 修复的效果。如果问题持续出现，再考虑添加预处理逻辑。

---

## 📝 总结

### 修改内容

1. ✅ 更新 `backend/prompts/curriculum_architect.j2`：添加禁止 Markdown 格式的明确说明
2. ✅ 更新 `backend/prompts/roadmap_editor.j2`：添加相同的格式要求

### 预期效果

- **消除 YAML 解析错误**：LLM 不再在 YAML 字段值中使用 Markdown 格式
- **提高系统稳定性**：减少因格式问题导致的任务失败
- **保持可读性**：输出内容仍然清晰，只是去掉了不必要的格式标记

### 后续跟进

1. 监控生产环境日志，确认解析错误是否消除
2. 收集用户反馈，验证输出质量是否受影响
3. 如有需要，考虑添加预处理逻辑作为额外保障

