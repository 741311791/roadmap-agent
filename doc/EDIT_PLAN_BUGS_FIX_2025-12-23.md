# Edit Plan 相关 Bug 修复报告
**日期**: 2025-12-23  
**任务**: 修复 Edit Plan 阶段的前端显示问题和后端数据库错误

---

## 问题汇总

### 问题1: 前端骨架加载状态异常
**现象**: 当工作流运行到 `edit_plan` 或 `validation_edit_plan` 阶段时，Learning Path Overview 模块始终显示骨架加载动画，而不是正常内容。

**根本原因**: `CoreDisplayArea` 组件中的 `shouldShowIntentCard` 和 `shouldShowRoadmap` 函数的步骤白名单中缺少 `edit_plan` 和 `validation_edit_plan` 步骤。

**影响**: 用户体验差，无法看到已生成的需求分析和路线图内容。

---

### 问题2: 数据库类型不匹配错误
**现象**: 后端抛出 PostgreSQL 错误：
```
(sqlalchemy.dialects.postgresql.asyncpg.Error) <class 'asyncpg.exceptions.DataError'>: 
invalid input for query argument $10: 0.3 (expected str, got float)
```

**根本原因**: 
- **Database 模型**（`EditPlanRecord`）定义 `confidence` 为 `Optional[str]` 类型，期望值为 `"high"/"medium"/"low"`
- **Domain 模型**（`EditPlanAnalyzerOutput`）定义 `confidence` 为 `float` 类型（0-1范围）
- **Repository 层**没有做类型转换，直接将 `float` 传给数据库

**影响**: Edit Plan 无法保存到数据库，阻塞工作流执行。

---

### 问题3: JSON 解析错误
**现象**: 日志中频繁出现 `edit_plan_analysis_json_parse_error`：
```
error='Expecting value: line 1 column 1 (char 0)'
content_preview='```json\n{\n  "feedback_summary": "...'
```

**根本原因**: 
- LLM 有时会在返回的 JSON 外包裹 markdown 代码块（\`\`\`json ... \`\`\`）
- `EditPlanAnalyzerAgent` 缺少提取代码块的逻辑（而其他 Agent 如 `IntentAnalyzerAgent` 已经有这个逻辑）

**影响**: 解析失败时会回退到低置信度默认计划，导致修改效果不佳。

---

## 修复方案

### 修复1: 前端 - 添加 Edit Plan 步骤支持

**文件**: `frontend-next/components/task/core-display-area.tsx`

**改动**:
```typescript
// shouldShowIntentCard 函数
const stepsAfterIntent = [
  'curriculum_design',
  'framework_generation',
  'structure_validation',
  'edit_plan',                    // 新增：用户审核后的修改计划分析
  'validation_edit_plan',         // 新增：验证失败后的修改计划分析
  'roadmap_edit',
  // ... 其他步骤
];

// shouldShowRoadmap 函数
const stepsAfterDesign = [
  'structure_validation',
  'edit_plan',                    // 新增：用户审核后的修改计划分析
  'validation_edit_plan',         // 新增：验证失败后的修改计划分析
  'roadmap_edit',
  // ... 其他步骤
];
```

**效果**: Edit Plan 阶段会正常显示已有的需求分析和路线图内容。

---

### 修复2: 后端 - 添加 confidence 类型转换

**文件**: `backend/app/core/orchestrator/node_runners/edit_plan_runner.py`

**改动**:
```python
def confidence_to_level(confidence: float) -> str:
    """
    将置信度数值（0-1）转换为级别字符串
    
    Args:
        confidence: 置信度数值，范围 [0, 1]
        
    Returns:
        置信度级别：'high', 'medium', 'low'
    """
    if confidence >= 0.7:
        return "high"
    elif confidence >= 0.4:
        return "medium"
    else:
        return "low"


# 在调用 create_plan 时转换类型
plan_record = await edit_plan_repo.create_plan(
    task_id=state["task_id"],
    roadmap_id=state.get("roadmap_id"),
    feedback_id=feedback_id,
    edit_plan=result.edit_plan,
    confidence=confidence_to_level(result.confidence),  # 转换为字符串
    needs_clarification=result.needs_clarification,
    clarification_questions=result.clarification_questions,
)
```

**转换规则**:
| Float 范围 | String 值 |
|-----------|----------|
| >= 0.7    | "high"   |
| >= 0.4    | "medium" |
| < 0.4     | "low"    |

**效果**: 修复数据库类型不匹配错误，Edit Plan 可以正常保存。

---

### 修复3: 后端 - 增强 JSON 解析鲁棒性

**文件**: `backend/app/agents/edit_plan_analyzer.py`

**改动**:
```python
# 解析输出
content = response.choices[0].message.content

try:
    # 尝试提取 JSON（LLM可能返回带代码块的内容）
    json_content = content
    if "```json" in content:
        json_start = content.find("```json") + 7
        json_end = content.find("```", json_start)
        if json_end > json_start:
            json_content = content[json_start:json_end].strip()
    elif "```" in content:
        json_start = content.find("```") + 3
        json_end = content.find("```", json_start)
        if json_end > json_start:
            json_content = content[json_start:json_end].strip()
    
    # 如果提取后是空字符串，尝试直接解析
    if not json_content.strip():
        json_content = content
    
    result_dict = json.loads(json_content)
    # ... 后续处理
    
except json.JSONDecodeError as e:
    logger.error(
        "edit_plan_analysis_json_parse_error",
        error=str(e),
        content_preview=content[:500],
        raw_content=content,  # 记录完整原始内容用于调试
        json_content_tried=json_content[:200] if 'json_content' in locals() else None,
    )
    # 返回低置信度默认计划...
```

**效果**: 
- 可以正确处理 LLM 返回的 markdown 代码块格式
- 增强错误日志，记录原始 LLM 响应以便调试
- 提升 JSON 解析成功率

---

## 测试建议

### 1. 前端测试
- [ ] 创建新任务，观察 `edit_plan` 阶段时 Learning Path Overview 是否正常显示
- [ ] 提交用户反馈触发修改，确认内容不会消失

### 2. 后端测试
- [ ] 触发 Edit Plan 流程，检查 PostgreSQL 日志确认无类型错误
- [ ] 查询 `edit_plan_records` 表，验证 `confidence` 字段为字符串类型（"high"/"medium"/"low"）

### 3. JSON 解析测试
- [ ] 观察后端日志，`edit_plan_analysis_json_parse_error` 频率应显著降低
- [ ] 如果仍有解析错误，检查 `raw_content` 日志分析 LLM 返回格式

---

## 相关文件

### 前端
- `frontend-next/components/task/core-display-area.tsx`

### 后端
- `backend/app/core/orchestrator/node_runners/edit_plan_runner.py`
- `backend/app/agents/edit_plan_analyzer.py`
- `backend/app/models/database.py` (EditPlanRecord 定义)
- `backend/app/models/domain.py` (EditPlanAnalyzerOutput 定义)
- `backend/app/db/repositories/review_feedback_repo.py` (EditPlanRepository)

---

## 后续优化建议

### 1. 统一 confidence 类型定义
**问题**: Domain 层和 Database 层对 confidence 的类型定义不一致，容易引发混淆。

**建议**:
- **方案A**: 统一使用 `str` 类型（"high"/"medium"/"low"），Domain 层也改为字符串
- **方案B**: 统一使用 `float` 类型（0-1），Database 层也改为浮点数
- **方案C**: 在 Pydantic 模型中添加自动类型转换 validator

**推荐**: 方案C，在 Domain 模型中保持语义化（"high"/"medium"/"low"），添加 validator 自动转换。

### 2. 提取 JSON 解析逻辑为工具函数
**问题**: 多个 Agent（IntentAnalyzer, EditPlanAnalyzer, ModificationAnalyzer 等）都有重复的 JSON 提取代码。

**建议**: 创建 `backend/app/utils/json_parser.py`:
```python
def extract_json_from_llm_response(content: str) -> str:
    """从 LLM 响应中提取 JSON 内容（处理代码块包裹）"""
    if "```json" in content:
        json_start = content.find("```json") + 7
        json_end = content.find("```", json_start)
        if json_end > json_start:
            return content[json_start:json_end].strip()
    elif "```" in content:
        json_start = content.find("```") + 3
        json_end = content.find("```", json_start)
        if json_end > json_start:
            return content[json_start:json_end].strip()
    
    # 尝试找到 JSON 对象
    start = content.find("{")
    end = content.rfind("}") + 1
    if start >= 0 and end > start:
        return content[start:end]
    
    return content.strip()
```

然后在所有 Agent 中复用。

### 3. 添加前端步骤管理工具
**问题**: 步骤白名单分散在多个函数中，容易遗漏。

**建议**: 创建 `frontend-next/lib/workflow-steps.ts`:
```typescript
// 工作流步骤枚举
export const WORKFLOW_STEPS = {
  INTENT_ANALYSIS: 'intent_analysis',
  CURRICULUM_DESIGN: 'curriculum_design',
  STRUCTURE_VALIDATION: 'structure_validation',
  EDIT_PLAN: 'edit_plan',
  VALIDATION_EDIT_PLAN: 'validation_edit_plan',
  ROADMAP_EDIT: 'roadmap_edit',
  // ...
} as const;

// 步骤分组
export const STEP_GROUPS = {
  AFTER_INTENT: [
    WORKFLOW_STEPS.CURRICULUM_DESIGN,
    WORKFLOW_STEPS.STRUCTURE_VALIDATION,
    WORKFLOW_STEPS.EDIT_PLAN,
    WORKFLOW_STEPS.VALIDATION_EDIT_PLAN,
    // ...
  ],
  AFTER_DESIGN: [
    WORKFLOW_STEPS.STRUCTURE_VALIDATION,
    WORKFLOW_STEPS.EDIT_PLAN,
    WORKFLOW_STEPS.VALIDATION_EDIT_PLAN,
    // ...
  ],
};

// 工具函数
export function shouldShowIntentCard(step: string): boolean {
  return STEP_GROUPS.AFTER_INTENT.includes(step);
}
```

---

## 总结

本次修复解决了 Edit Plan 相关的三个关键问题：

1. ✅ **前端显示**: 添加了 `edit_plan` 和 `validation_edit_plan` 步骤支持
2. ✅ **数据库错误**: 添加了 confidence 类型转换逻辑
3. ✅ **JSON 解析**: 增强了 LLM 响应解析的鲁棒性

所有修改都遵循了现有代码风格，并添加了详细的中文注释。


