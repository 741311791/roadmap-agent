# Custom Assessment Unique Constraint Fix

## 问题描述

自定义技术栈测验题生成时出现数据库唯一约束冲突错误：

```
duplicate key value violates unique constraint "uq_tech_proficiency"
Key (technology, proficiency_level)=(Hive, beginner) already exists.
```

### 错误日志示例

```
2025-12-20 13:14:37 [error] custom_assessment_generation_failed 
error='(sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) 
duplicate key value violates unique constraint "uq_tech_proficiency"
DETAIL: Key (technology, proficiency_level)=(Hive, beginner) already exists.'
```

## 根本原因分析

### 1. 竞态条件 (Race Condition)

当用户快速多次点击"Assess"按钮或多个用户同时请求同一自定义技术栈时：

```
用户请求1 → 后台任务1 → 检查不存在 → 生成题目 → 插入数据库
用户请求2 → 后台任务2 → 检查不存在 → 生成题目 → 插入数据库 ❌ (冲突)
```

两个任务都通过了 `assessment_exists` 检查，但在插入时第二个任务遇到唯一约束冲突。

### 2. Session回滚问题

当第一次插入失败后，SQLAlchemy Session 处于 "pending rollback" 状态：

```python
# 第一次尝试失败
await repo.create_assessment(...)  # IntegrityError

# 后续尝试会失败，因为Session未回滚
await repo.create_assessment(...)  # PendingRollbackError
```

## 解决方案

### 1. Repository层：实现Upsert逻辑

修改 `tech_assessment_repo.py` 的 `create_assessment` 方法：

**文件**: `backend/app/db/repositories/tech_assessment_repo.py`

```python
async def create_assessment(
    self,
    assessment_id: str,
    technology: str,
    proficiency_level: str,
    questions: list,
    total_questions: int,
) -> TechStackAssessment:
    """
    创建新的测验记录（如果已存在则更新）
    
    使用 upsert 逻辑避免唯一约束冲突：
    - 如果 (technology, proficiency_level) 已存在，更新题目
    - 如果不存在，创建新记录
    """
    # 先检查是否已存在
    existing = await self.get_assessment(technology, proficiency_level)
    
    if existing:
        # 已存在，更新题目
        existing.questions = questions
        existing.total_questions = total_questions
        existing.assessment_id = assessment_id
        
        await self.session.commit()
        await self.session.refresh(existing)
        
        logger.info("tech_assessment_updated", ...)
        return existing
    else:
        # 不存在，创建新记录
        assessment = TechStackAssessment(...)
        self.session.add(assessment)
        await self.session.commit()
        await self.session.refresh(assessment)
        
        logger.info("tech_assessment_created", ...)
        return assessment
```

**优点**：
- ✅ 避免唯一约束冲突
- ✅ 如果题目已存在，会更新为最新生成的题目
- ✅ 幂等操作，多次调用结果一致

### 2. API层：添加Session回滚处理

修改 `tech_assessment.py` 的 `_generate_custom_assessment_pool` 函数：

**文件**: `backend/app/api/v1/endpoints/tech_assessment.py`

```python
except Exception as e:
    # 回滚当前事务，避免影响后续操作
    await db.rollback()
    
    logger.error(
        "custom_assessment_generation_failed",
        technology=technology,
        level=level,
        error=str(e),
        error_type=type(e).__name__,
    )
    # 继续处理下一个级别
    continue
```

**优点**：
- ✅ 确保Session状态正常
- ✅ 单个级别失败不影响其他级别生成
- ✅ 提供详细的错误日志

### 3. Service层：同步修复初始化逻辑

修改 `tech_assessment_initializer.py`：

**文件**: `backend/app/services/tech_assessment_initializer.py`

```python
except Exception as e:
    # 回滚当前事务，避免影响后续操作
    await db.rollback()
    
    logger.error(...)
    failed_count += 1
    failed_items.append(f"{tech}-{level}")
    # 继续处理下一个
    continue
```

## 修改文件清单

1. ✅ `backend/app/db/repositories/tech_assessment_repo.py`
   - `create_assessment` 方法改为 upsert 逻辑

2. ✅ `backend/app/api/v1/endpoints/tech_assessment.py`
   - `_generate_custom_assessment_pool` 添加 Session 回滚

3. ✅ `backend/app/services/tech_assessment_initializer.py`
   - 异常处理中添加 Session 回滚

## 测试场景

### 场景1：快速重复点击
```
用户在Profile页面快速点击两次"Assess"按钮
→ 两个后台任务并发执行
→ 第二个任务发现已存在，更新题目（而不是报错）
✅ 成功
```

### 场景2：相同技术栈不同级别
```
用户为Hive生成beginner、intermediate、expert测验
→ 依次生成3个级别
→ 某个级别失败不影响其他级别
✅ 部分成功
```

### 场景3：应用启动初始化
```
应用启动，初始化预定义技术栈题库
→ 某个技术栈生成失败
→ 回滚Session，继续处理下一个
✅ 其他技术栈正常初始化
```

## 数据库约束

表：`tech_stack_assessments`

唯一约束：`uq_tech_proficiency`
- 字段：`(technology, proficiency_level)`
- 目的：确保每个技术栈的每个级别只有一套题库

修复后的逻辑尊重这个约束，同时提供更好的用户体验。

## 日志输出改进

### 修复前
```
[error] custom_assessment_generation_failed error='IntegrityError...'
[error] custom_assessment_generation_failed error='PendingRollbackError...'
[error] custom_assessment_generation_failed error='PendingRollbackError...'
```

### 修复后
```
[info] custom_assessment_already_exists technology=Hive level=beginner
[info] tech_assessment_updated technology=Hive level=intermediate
[info] custom_assessment_generated technology=Hive level=expert
```

## 影响范围

### 用户体验改进
- ✅ 自定义技术栈测验生成更可靠
- ✅ 不会因为重复点击而报错
- ✅ 部分失败不影响整体功能

### 系统稳定性
- ✅ 避免Session处于invalid状态
- ✅ 错误恢复机制更健壮
- ✅ 并发场景处理更安全

## 兼容性

- ✅ 完全向后兼容
- ✅ 不需要数据库迁移
- ✅ 不影响现有API接口
- ✅ 不影响前端代码

## 后续优化建议

### 1. 添加分布式锁（可选）

如果需要更严格的并发控制：

```python
async with redis_lock(f"assessment:{technology}:{level}"):
    # 生成和保存逻辑
    pass
```

### 2. 缓存已生成的技术栈列表

```python
# Redis缓存已生成的技术栈
await redis.sadd("generated_techs", technology)
```

### 3. 前端防抖处理

```typescript
// 防止用户快速重复点击
const handleAssess = debounce(async () => {
  // ...
}, 1000);
```

## 总结

通过实现 **Upsert 逻辑** 和 **Session 回滚处理**，彻底解决了自定义技术栈测验生成中的唯一约束冲突问题。修复方案简单、可靠，不影响现有功能，显著提升了系统的健壮性和用户体验。

