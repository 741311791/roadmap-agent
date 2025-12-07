# 🔧 CurriculumArchitect 参数缺失修复

## 问题描述

**错误信息**:
```
TypeError: CurriculumArchitectAgent.design() missing 1 required positional argument: 'roadmap_id'
```

**发生位置**: `backend/app/agents/curriculum_architect.py:849`

## 根本原因

`curriculum_runner.py` 传递了 3 个参数给 `execute()` 方法：
- `intent_analysis`
- `user_preferences` 
- `roadmap_id` ✅

但 `curriculum_architect.py` 的 `execute()` 方法只转发了 2 个参数给 `design()` 方法：
- `intent_analysis` ✅
- `user_preferences` ✅
- ~~`roadmap_id`~~ ❌ 缺失！

## 修复方案

### 修改文件: `backend/app/agents/curriculum_architect.py`

**修复前** (第 847-852 行):
```python
async def execute(self, input_data: dict) -> CurriculumDesignOutput:
    """实现基类的抽象方法"""
    return await self.design(
        intent_analysis=input_data["intent_analysis"],
        user_preferences=input_data["user_preferences"],
    )  # ❌ 缺少 roadmap_id
```

**修复后**:
```python
async def execute(self, input_data: dict) -> CurriculumDesignOutput:
    """实现基类的抽象方法"""
    return await self.design(
        intent_analysis=input_data["intent_analysis"],
        user_preferences=input_data["user_preferences"],
        roadmap_id=input_data["roadmap_id"],  # ✅ 添加 roadmap_id
    )
```

## 验证

修复后，路线图生成流程应该能正常通过 `curriculum_design` 阶段：

```
✅ intent_analysis → 完成
✅ curriculum_design → 现在应该成功
✅ 后续步骤继续...
```

## 测试

重新发起路线图生成请求，观察日志：

**预期日志**:
```log
[info] curriculum_design_started
[info] curriculum_design_calling_llm
[info] curriculum_design_completed 
       roadmap_id=xxx 
       stages_count=4
```

**不应该出现**:
```log
❌ TypeError: CurriculumArchitectAgent.design() missing 1 required positional argument
```

---

**修复时间**: 2025-12-07  
**状态**: ✅ 完成

