# Curriculum Architect Agent - current_level 适配修复

**日期**: 2026-01-26  
**类型**: Bug Fix  
**影响范围**: 后端 Agent 层 - 课程设计逻辑

---

## 问题描述

**用户反馈**：Curriculum Architect Agent（课程架构师）在设计路线图结构时完全没有考虑用户的当前水平（`current_level`）。

**问题根源**：
虽然 `curriculum_architect.py` 在构建用户消息时**已经传递了** `current_level` 参数，但 Prompt 模板 `curriculum_architect.j2` 中**没有明确强调**这个信息的重要性，导致 LLM 在设计路线图时可能忽略用户的当前水平。

### 代码层面验证

- ✅ **Agent 代码正确**：`curriculum_architect.py` 第612行（非流式）和第830行（流式）都正确传递了 `current_level`
- ❌ **Prompt 模板缺陷**：`curriculum_architect.j2` 的 Context Injection 部分没有明确提示 LLM 关注 `current_level`

---

## 修复方案

### 修改文件

**文件路径**: `backend/prompts/curriculum_architect.j2`

### 修改内容

#### 1. Context Injection 部分 - 添加 current_level 强调

在 `[2. Context Injection]` 部分的语言偏好设置之后，新增：

```jinja2
**🔴 [CRITICAL] 用户当前水平（必须在设计中体现）**：
用户在 user_message 中会明确说明其当前水平（current_level）。你**必须**根据这个水平调整路线图的起点和难度：
- **beginner（初学者）**：从最基础的概念开始，包含环境搭建、基本语法等入门内容
- **intermediate（中级）**：跳过基础知识，直接从核心概念和框架使用开始
- **advanced（高级）**：聚焦于高级特性、架构设计、性能优化等深度内容
- **expert（专家）**：只包含前沿技术、最佳实践、系统设计等专业内容
```

#### 2. Constraints & Rules 部分 - 强化设计原则

修改 `**设计原则：**` 第一条（渐进式难度），添加根据 `current_level` 调整起点的说明：

```jinja2
1. **渐进式难度**：Stage 之间遵循"基础→进阶→实战"的递进逻辑
   - ⚠️ **根据用户当前水平调整起点**：
     * beginner：Stage 1 从环境搭建、基础语法开始
     * intermediate：Stage 1 从框架核心概念、常用API开始（跳过基础语法）
     * advanced：Stage 1 从高级特性、架构模式开始（跳过基础和入门内容）
     * expert：直接聚焦深度主题（性能优化、系统设计、源码分析）
   - Stage 1-2：基础知识和核心概念（根据 current_level 调整）
   - Stage 3-4：进阶技能和实际应用
   - Stage 5（如有）：综合项目和生产实践
```

#### 3. Examples 部分 - 强化示例说明

**示例 1**（beginner）：
```jinja2
**示例 1：前端开发路线图（4 个 Stage）- 初学者**

需求分析：
- 学习目标：成为前端工程师
- 关键技术栈：["HTML", "CSS", "JavaScript", "React", "TypeScript"]
- **当前水平：beginner** ← ⚠️ 注意：从最基础的HTML标签开始
- 每周可投入：15 小时

输出格式（JSON）：
{
  "design_rationale": "该路线图针对零基础初学者（beginner），从最基础的HTML标签和CSS样式开始，采用渐进式设计，逐步过渡到JavaScript、现代框架React，最后通过实战项目巩固，确保学习者能够系统掌握前端开发全栈技能。",
  ...
}
```

**示例 2**（intermediate）：
```jinja2
**示例 2：Python 数据分析路线图（3 个 Stage）- 中级学习者**

需求分析：
- 学习目标：掌握数据分析技能
- 关键技术栈：["Python", "Pandas", "Matplotlib", "SQL"]
- **当前水平：intermediate（已懂 Python 基础）** ← ⚠️ 注意：跳过了Python基础语法
- 每周可投入：10 小时

输出格式（JSON）：
{
  "roadmap_id": "python-data-analysis",
  "title": "Python数据分析学习路线",
  "design_rationale": "该路线图针对已有Python基础的学习者（intermediate），直接从数据分析核心技能开始，跳过Python语法等基础内容，聚焦Pandas、NumPy、可视化和统计分析，最后通过综合项目巩固所学知识。",
  "stages": [
    {
      "stage_id": "stage-1",
      "name": "数据处理基础",
      "description": "掌握Pandas和NumPy核心功能（假设用户已掌握Python基础语法）",
      ...
    }
  ]
}
```

**新增示例 3**（对比不同 current_level）：
```jinja2
**示例 3：同一学习目标，不同 current_level 的对比**

**场景A：beginner 学习 React**
- current_level: beginner
- Stage 1 必须包含：HTML基础、CSS基础、JavaScript基础（变量、函数、DOM操作）
- Stage 2：React 入门（组件、JSX、Props）
- Stage 3：React 进阶（Hooks、状态管理）

**场景B：intermediate 学习 React**
- current_level: intermediate（已掌握 HTML/CSS/JS 基础）
- Stage 1 直接从：React 核心概念（组件、JSX、Props、State）开始 ← ⚠️ 跳过了HTML/CSS/JS基础
- Stage 2：Hooks 和副作用管理
- Stage 3：状态管理（Redux/Zustand）和实战项目

**场景C：advanced 学习 React**
- current_level: advanced（已有 React 项目经验）
- Stage 1 直接从：性能优化（React.memo、useMemo、useCallback）开始 ← ⚠️ 跳过了基础和入门内容
- Stage 2：并发模式（Suspense、useTransition）
- Stage 3：架构设计（微前端、SSR/SSG、monorepo）
```

#### 4. Quality Checklist 部分 - 添加检查项

在 `[7. Quality Checklist]` 的第一项新增：

```jinja2
- [ ] **🔴 路线图起点是否匹配用户的 current_level？**
  - beginner：Stage 1 包含环境搭建、基础语法等入门内容
  - intermediate：Stage 1 从核心概念/框架使用开始（跳过基础）
  - advanced：Stage 1 从高级特性开始（跳过基础和入门）
  - expert：直接聚焦深度主题（性能优化、架构设计）
```

---

## 预期效果

修复后，Curriculum Architect Agent 将会：

1. **明确识别用户的 current_level**：在设计路线图前优先考虑用户当前水平
2. **调整路线图起点**：
   - 初学者：从最基础的环境搭建和语法开始
   - 中级学习者：跳过基础语法，直接从框架核心概念开始
   - 高级学习者：跳过入门和基础内容，聚焦高级特性和架构设计
   - 专家：只包含前沿技术、性能优化、系统设计等深度内容
3. **优化学习路径**：避免向有经验的学习者推荐过于基础的内容，提高学习效率

---

## 测试建议

### 测试用例

**用例 1：beginner 学习 Python**
- 输入：`current_level: beginner`, `learning_goal: "学习Python编程"`
- 预期：Stage 1 包含 "Python 环境搭建"、"变量与数据类型"、"基础语法" 等概念

**用例 2：intermediate 学习 Python Web 开发**
- 输入：`current_level: intermediate`, `learning_goal: "学习 FastAPI 框架"`
- 预期：Stage 1 **跳过** Python 基础语法，直接从 "FastAPI 路由系统"、"依赖注入" 等概念开始

**用例 3：advanced 学习 React**
- 输入：`current_level: advanced`, `learning_goal: "深入学习 React"`
- 预期：Stage 1 **跳过** 组件基础和 Hooks 入门，直接从 "性能优化"、"并发模式" 等高级主题开始

---

## 相关文件

- **修改文件**: `backend/prompts/curriculum_architect.j2`
- **相关代码**: `backend/app/agents/curriculum_architect.py` (第612行、第830行)
- **数据模型**: `backend/app/models/domain.py` (LearningPreferences.current_level)

---

## 总结

本次修复通过在 Prompt 模板中**明确强调** `current_level` 的重要性，确保 LLM 在设计路线图时充分考虑用户的当前水平，从而生成更符合用户实际需求的个性化学习路径。

**关键改进点**：
1. ✅ Context Injection 明确标注 current_level 为 CRITICAL 信息
2. ✅ 设计原则中添加根据 current_level 调整起点的具体指导
3. ✅ 示例中明确展示不同 current_level 的路线图差异
4. ✅ Quality Checklist 中强制要求检查 current_level 适配性
