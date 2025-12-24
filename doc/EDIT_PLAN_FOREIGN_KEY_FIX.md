# Edit Plan 外键约束违规修复 (2025-12-23)

## 问题描述

**错误信息**：
```
(sqlalchemy.dialects.postgresql.asyncpg.IntegrityError) <class 'asyncpg.exceptions.ForeignKeyViolationError'>: 
insert or update on table "edit_plan_records" violates foreign key constraint "edit_plan_records_feedback_id_fkey"
DETAIL: Key (feedback_id)=(5f89078d-a778-40b1-bb22-8a8e5236767b) is not present in table "human_review_feedbacks".
```

**问题原因**：
在工作流中，`ReviewRunner` 创建 `HumanReviewFeedback` 记录后，没有提交数据库事务。虽然使用了 `flush=True` 将更改刷新到会话，但事务从未提交，导致记录实际上并未保存到数据库中。

当后续的 `EditPlanRunner` 尝试创建 `EditPlanRecord` 并引用该 `feedback_id` 时，由于外键约束检查发现 `human_review_feedbacks` 表中不存在该记录，导致抛出外键约束违规错误。

## 根本原因分析

### BaseRepository.create() 行为

从 `BaseRepository.create()` 方法的实现可以看到：

```python
async def create(self, entity: T, *, flush: bool = False) -> T:
    self.session.add(entity)
    
    if flush:
        await self.session.flush()
        await self.session.refresh(entity)
    
    return entity
```

**关键点**：
- `flush=True` 只是将更改刷新到数据库会话，**不会提交事务**
- 必须显式调用 `await session.commit()` 才能永久保存到数据库
- 如果会话在没有提交的情况下关闭，所有更改都会回滚

### 错误代码模式

**review_runner.py (第197-236行)**：
```python
async with AsyncSessionLocal() as session:
    feedback_repo = ReviewFeedbackRepository(session)
    
    feedback_record = await feedback_repo.create_feedback(...)
    # ❌ 缺少：await session.commit()
    
    logger.info("review_feedback_saved_to_db", ...)
# 当 async with 块结束时，会话被关闭，但事务未提交！
```

**edit_plan_runner.py (第174-214行)**：
```python
async with AsyncSessionLocal() as session:
    edit_plan_repo = EditPlanRepository(session)
    
    plan_record = await edit_plan_repo.create_plan(...)
    # ❌ 缺少：await session.commit()
    
    logger.info("edit_plan_saved_to_db", ...)
```

## 修复方案

### 1. review_runner.py 修复

在 `HumanReviewFeedback` 创建后，添加事务提交：

```python
async with AsyncSessionLocal() as session:
    feedback_repo = ReviewFeedbackRepository(session)
    
    feedback_record = await feedback_repo.create_feedback(
        task_id=task_id,
        roadmap_id=roadmap_id,
        user_id=user_id,
        approved=approved,
        feedback_text=feedback if feedback else None,
        roadmap_version_snapshot=roadmap_snapshot,
        review_round=current_round,
    )
    
    # ✅ 关键修复：提交事务以确保记录真正保存到数据库
    await session.commit()
    
    logger.info("review_feedback_saved_to_db", ...)
```

### 2. edit_plan_runner.py 修复

在 `EditPlanRecord` 创建后，添加事务提交：

```python
async with AsyncSessionLocal() as session:
    edit_plan_repo = EditPlanRepository(session)
    
    plan_record = await edit_plan_repo.create_plan(
        task_id=state["task_id"],
        roadmap_id=state.get("roadmap_id"),
        feedback_id=feedback_id,
        edit_plan=result.edit_plan,
        confidence=confidence_to_level(result.confidence),
        needs_clarification=result.needs_clarification,
        clarification_questions=result.clarification_questions,
    )
    
    # ✅ 关键修复：提交事务以确保记录真正保存到数据库
    await session.commit()
    
    edit_plan_record_id = plan_record.id
    logger.info("edit_plan_saved_to_db", ...)
```

## 影响范围

### 修改的文件
1. `backend/app/core/orchestrator/node_runners/review_runner.py` (第223行添加 commit)
2. `backend/app/core/orchestrator/node_runners/edit_plan_runner.py` (第193行添加 commit)

### 不受影响的文件
检查了所有其他 runner 文件，仅这两个文件使用了 `AsyncSessionLocal` 直接创建会话：
- ✅ `validation_edit_plan_runner.py` - 未使用 `AsyncSessionLocal`
- ✅ `editor_runner.py` - 未使用 `AsyncSessionLocal`
- ✅ `validation_runner.py` - 未使用 `AsyncSessionLocal`
- ✅ `content_runner.py` - 未使用 `AsyncSessionLocal`
- ✅ `curriculum_runner.py` - 未使用 `AsyncSessionLocal`
- ✅ `intent_runner.py` - 未使用 `AsyncSessionLocal`

## 测试验证

### 验证步骤
1. 启动工作流，生成路线图
2. 在人工审核节点拒绝路线图并提供反馈
3. 检查数据库：
   - `human_review_feedbacks` 表应包含反馈记录
   - `edit_plan_records` 表应包含修改计划记录
   - 外键关联应正确建立
4. 后端日志应显示：
   ```
   review_feedback_saved_to_db
   edit_plan_saved_to_db
   ```

### 预期结果
- ✅ 不再出现外键约束违规错误
- ✅ 用户反馈和修改计划均成功保存到数据库
- ✅ 工作流正常继续执行

## 最佳实践总结

### 使用 Repository 时的事务管理规则

1. **创建会话后必须提交**：
   ```python
   async with AsyncSessionLocal() as session:
       repo = SomeRepository(session)
       record = await repo.create_something(...)
       await session.commit()  # ✅ 必须显式提交
   ```

2. **flush vs commit**：
   - `flush=True`: 将更改刷新到会话，可以获取数据库生成的 ID，但**不提交事务**
   - `commit()`: 提交事务，永久保存更改到数据库

3. **异常处理**：
   ```python
   async with AsyncSessionLocal() as session:
       try:
           repo = SomeRepository(session)
           record = await repo.create_something(...)
           await session.commit()
       except Exception as e:
           await session.rollback()  # 发生错误时回滚
           raise
   ```

4. **为什么不在 BaseRepository 中自动提交？**
   - 支持批量操作：多个创建/更新操作可以在一个事务中完成
   - 调用者控制事务边界：允许更灵活的事务管理
   - 符合 Repository 模式：Repository 负责数据访问，事务管理由调用者负责

## 相关文档
- `HUMAN_REVIEW_FEEDBACK_PERSISTENCE.md` - 原始功能实现文档
- `backend/app/db/repositories/base.py` - BaseRepository 实现
- `backend/tests/unit/test_repository_base.py` - Repository 测试用例（展示了正确的事务提交模式）

