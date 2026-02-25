# test_human_review.py 脚本重构

**日期**: 2026-02-07  
**类型**: 重构  
**文件**: `backend/scripts/test_human_review.py`

## 重构目标

简化测试脚本，移除自动化功能，保留交互式审核功能，增加状态管理功能。

## 移除的功能

### 1. 创建新任务功能
- ❌ 移除 `create_roadmap_task()` 函数
- ❌ 移除 `--create-new` 参数
- ❌ 移除创建任务的相关逻辑

### 2. 自动批准功能
- ❌ 移除 `--auto-approve` 参数
- ❌ 移除自动批准逻辑

### 3. 自动拒绝功能
- ❌ 移除 `--auto-reject` 参数
- ❌ 移除 `--feedback` 参数（作为独立参数）
- ❌ 移除自动拒绝逻辑

### 4. 等待审核功能
- ❌ 移除 `wait_for_human_review()` 函数
- ❌ 移除轮询配置（`POLL_INTERVAL`, `MAX_POLL_ATTEMPTS`）

## 保留的功能

### 1. 交互式审核功能 ✅
- ✅ 保留 `submit_approval()` 函数
- ✅ 查找待审核任务
- ✅ 用户选择要审核的任务
- ✅ 交互式输入批准/拒绝决策
- ✅ 拒绝时可输入反馈意见

## 新增的功能

### 1. 列出任务功能
```bash
# 列出所有任务，按状态分组
uv run python scripts/test_human_review.py --list
```

**输出示例**:
```
======================================================================
📋 用户信息
======================================================================
  User ID: uuid-xxx
  Email: test@example.com
  Username: test_user
======================================================================

======================================================================
📊 任务列表（共 5 个任务）
======================================================================

[HUMAN_REVIEW_PENDING] - 2 个任务:
----------------------------------------------------------------------
  • Task ID: task-123
    标题: 学习全栈开发
    创建时间: 2026-02-07T10:00:00Z
    当前步骤: human_review

  • Task ID: task-456
    标题: Python进阶
    创建时间: 2026-02-07T11:00:00Z
    当前步骤: human_review

[COMPLETED] - 3 个任务:
----------------------------------------------------------------------
  ...

======================================================================

💡 提示：使用 --reset <task_id> 可以将任务重置为待审核状态
```

### 2. 重置任务状态功能
```bash
# 重置指定任务为 human_review_pending 状态
uv run python scripts/test_human_review.py --reset <task_id>
```

**新增函数**:
```python
async def reset_task_to_review(
    client: httpx.AsyncClient,
    token: str,
    task_id: str,
) -> bool:
    """
    重置任务状态为 human_review_pending
    
    调用后端 API:
    POST /api/v1/tasks/{task_id}/reset-to-review
    """
```

## 代码结构对比

### 重构前
```python
# 主要函数
- login()
- get_user_tasks()
- create_roadmap_task()          # ❌ 已移除
- get_task_status()
- wait_for_human_review()        # ❌ 已移除
- submit_approval()              # ✅ 保留
- get_user_info()
- main_interactive()             # ❌ 已重构

# 命令行参数
--create-new                     # ❌ 已移除
--auto-approve                   # ❌ 已移除
--auto-reject                    # ❌ 已移除
--feedback                       # ❌ 已移除（作为独立参数）
```

### 重构后
```python
# 主要函数
- login()
- get_user_tasks()
- get_task_status()
- submit_approval()              # ✅ 保留
- reset_task_to_review()         # ✅ 新增
- get_user_info()
- interactive_review_main()      # ✅ 新增（交互式审核）
- list_tasks_main()              # ✅ 新增（列出任务）
- reset_task_main()              # ✅ 新增（重置状态）

# 命令行参数
（默认）                          # ✅ 交互式审核
--list                           # ✅ 新增
--reset <task_id>                # ✅ 新增
```

## 使用方式

### 1. 交互式审核（默认模式）
```bash
cd backend
uv run python scripts/test_human_review.py
```

**流程**:
1. 自动查找所有 `human_review_pending` 状态的任务
2. 用户选择要审核的任务
3. 用户选择批准（1）或拒绝（2）
4. 如果拒绝，用户输入反馈意见
5. 提交审核决策到后端

### 2. 列出所有任务
```bash
cd backend
uv run python scripts/test_human_review.py --list
```

### 3. 重置任务状态
```bash
cd backend
uv run python scripts/test_human_review.py --reset task-123-abc
```

## 后续需要的后端支持

脚本中调用了以下 API 端点，需要后端实现：

```http
POST /api/v1/tasks/{task_id}/reset-to-review
Authorization: Bearer {token}
```

**预期响应**:
```json
{
  "success": true,
  "message": "任务状态已重置",
  "data": {
    "task_id": "task-123",
    "old_status": "completed",
    "new_status": "human_review_pending"
  }
}
```

## 优势

1. **保留核心功能**: 保留了交互式人工审核功能（批准/拒绝）
2. **移除自动化**: 移除了自动批准/拒绝等测试自动化功能，更符合真实审核场景
3. **增强灵活性**: 新增任务状态重置功能，方便测试
4. **更清晰**: 三个独立模式（审核/列表/重置），职责明确
5. **更易维护**: 代码结构更简洁，移除了复杂的自动化逻辑

## 测试建议

1. **验证列表功能**: 运行脚本查看任务列表是否正确显示
2. **验证重置功能**: 需要后端实现 `/reset-to-review` 端点后测试
3. **错误处理**: 测试无效 task_id 的错误提示
