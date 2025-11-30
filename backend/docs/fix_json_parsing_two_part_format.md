# 修复 JSON 解析错误 - 采用两段式输出格式

## 问题描述

运行测试时遇到 JSON 解析错误：

```
json.decoder.JSONDecodeError: Unterminated string starting at: line 6 column 23 (char 269)
```

从日志可以看到，LLM 返回的 JSON 中 `tutorial_content` 字段包含了很长的 markdown 内容，导致：
1. JSON 字符串被截断（超过 `max_tokens` 限制）
2. 转义复杂容易出错
3. LLM 难以正确生成大型 JSON

## 根本原因

原始 Prompt 要求在 JSON 中嵌入完整的教程内容：

```json
{
  "tutorial_content": "# 很长很长的 markdown 内容...",
  ...
}
```

这种格式存在问题：
- **Token 限制**：即使 max_tokens=16384，也可能不够
- **转义复杂**：markdown 中的引号、换行符需要正确转义（`\n`, `\"`）
- **LLM 易出错**：生成长 JSON 时容易格式错误或被截断

## 解决方案：两段式输出格式

### 新格式

```
[Markdown 教程内容 - 无需转义]

===TUTORIAL_METADATA===
{
  "concept_id": "...",
  "tutorial_id": "...",
  "title": "...",
  "summary": "...",
  "estimated_completion_time": 90
}
```

### 优点

1. **Markdown 直接输出**：无需转义，LLM 更容易生成
2. **JSON 简短**：只包含元数据，不易出错
3. **分离关注点**：内容和元数据分开，更清晰
4. **兼容旧格式**：代码中保留了对旧格式的兼容处理

## 修改内容

### 1. Prompt 模板更新

**文件**: `backend/prompts/tutorial_generator.j2`

#### 修改 [4. Output Format]

```jinja2
[4. Output Format]
**采用两段式输出格式，确保稳定性：**

第一部分：完整的教程内容（Markdown格式）
第二部分：元数据（JSON格式）

使用以下分隔符分隔两部分：
===TUTORIAL_METADATA===
```

#### 修改 [5. Tool Usage Guide]

更新工具名称从 `web_search_v1` 改为 `web_search`（与函数调用一致）

#### 修改 [7. Examples]

提供两段式格式的完整示例

### 2. 代码解析逻辑更新

**文件**: `backend/app/agents/tutorial_generator.py`

#### 修改 `generate()` 方法

```python
# 新的两段式格式：Markdown 内容 + 分隔符 + JSON 元数据
separator = "===TUTORIAL_METADATA==="

if separator in content:
    # 解析两段式格式
    parts = content.split(separator, 1)
    tutorial_markdown = parts[0].strip()
    json_part = parts[1].strip()
    
    # 清理 JSON 部分（去除代码块标记）
    if json_part.startswith("```json"):
        json_part = json_part[7:]
    # ...
    
    metadata = json.loads(json_part)
else:
    # 兼容旧格式（向后兼容）
    # ...
```

#### 修改 `generate_stream()` 方法

使用相同的解析逻辑

## 输出格式示例

### 完整示例

```
# React Hooks 原理深入解析

## 概述

React Hooks 是 React 16.8 引入的新特性，允许在函数组件中使用状态和其他 React 特性。

## 前置知识回顾

在学习本概念之前，建议先掌握：
- React 基础概念
- 函数式编程基础

## 核心概念

### useState 详解

`useState` 是最常用的 Hook：

```javascript
const [count, setCount] = useState(0);
```

## 实践示例

### 示例 1: 计数器组件

```javascript
import React, { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);
  return (
    <div>
      <p>You clicked {count} times</p>
      <button onClick={() => setCount(count + 1)}>
        Click me
      </button>
    </div>
  );
}
```

## 总结

本教程介绍了 React Hooks 的核心概念和使用方法...

===TUTORIAL_METADATA===
{
  "concept_id": "react-hooks-001",
  "tutorial_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "React Hooks 原理深入解析",
  "summary": "本教程深入讲解 React Hooks 的设计原理、核心概念和实战应用，包括 useState、useEffect 等常用 Hooks 的使用方法，以及自定义 Hooks 的编写技巧。",
  "estimated_completion_time": 90
}
```

## 兼容性

- ✅ **向后兼容**：代码中保留了对旧格式（JSON 包含 `tutorial_content` 字段）的支持
- ✅ **自动检测**：根据是否存在分隔符自动选择解析方式
- ✅ **错误处理**：对两种格式都有完善的错误处理

## 测试

运行测试脚本验证：

```bash
cd backend
python scripts/test_tutorial_tool_calling.py
```

应该不再出现 JSON 解析错误。

## 其他改进

### 增加日志

```python
logger.info(
    "tutorial_generation_two_part_format_detected",
    concept_id=concept.concept_id,
    markdown_length=len(tutorial_markdown),
)
```

或

```python
logger.warning(
    "tutorial_generation_old_format_detected",
    concept_id=concept.concept_id,
    message="LLM 未使用两段式格式，尝试解析旧格式 JSON",
)
```

### 更好的错误信息

```python
if not tutorial_markdown:
    raise ValueError("教程内容为空")
```

## 影响范围

- ✅ `generate()` 方法 - 已更新
- ✅ `generate_stream()` 方法 - 已更新
- ✅ Prompt 模板 - 已更新
- ✅ 向后兼容 - 保留旧格式支持

## 预期效果

1. **不再出现 JSON 解析错误**
2. **LLM 生成更稳定**：markdown 不需要转义
3. **支持更长的教程**：没有 JSON 大小限制
4. **更清晰的输出**：内容和元数据分离

## 版本信息

- 修改日期：2024-11-29
- 问题：JSON 解析错误（Unterminated string）
- 解决方案：两段式输出格式
- 影响文件：
  - `backend/prompts/tutorial_generator.j2`
  - `backend/app/agents/tutorial_generator.py`

