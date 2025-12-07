# 路线图生成 Execution Logs 修复文档

## 前端实际调用的接口

### 主要接口（new/page.tsx 使用）

**前端调用端点**: `POST /api/v1/roadmaps/generate`（非流式）

**调用链**:
```
前端 (frontend-next/app/app/new/page.tsx)
  ↓ generateRoadmapAsync()
  ↓ POST /api/v1/roadmaps/generate
后端 (backend/app/api/v1/roadmap.py:115)
  ↓ generate_roadmap() 
  ↓ 创建后台任务 _execute_roadmap_generation_task()
  ↓ RoadmapService.generate_roadmap()
  ↓ RoadmapOrchestrator.execute()
    ↓ _run_intent_analysis()      ← execution_logs 记录点 ✅
    ↓ _run_curriculum_design()    ← execution_logs 记录点 ✅
    ↓ ... 其他步骤
```

**进度更新**: 通过 WebSocket（TaskWebSocket）推送实时进度

### 备用接口（roadmaps/create/page.tsx 使用）

**前端调用端点**: `POST /api/v1/roadmaps/generate-full-stream`（流式）

**端点位置**: `backend/app/api/v1/roadmap.py:962`

## 问题描述

前端发起路线图生成请求后，后端存在以下问题：

1. **需求分析结果未写入 execution_logs**：SSE流式接口中的需求分析（intent_analysis）步骤完成后，没有记录到 `roadmap.public.execution_logs` 表
2. **路线图架构图未写入 execution_logs**：课程架构设计（curriculum_design）步骤完成后，中间结果未记录到日志表
3. **compact_roadmap_parse_error**：简洁格式路线图解析错误，缺少详细的错误信息和容错处理
4. **数据库写入缺少日志记录**：路线图保存到数据库的过程没有记录到 execution_logs

## 修复方案

### 1. SSE 流式接口添加 execution_logs 记录

**文件**: `backend/app/api/v1/roadmap.py` - `_generate_sse_stream()` 函数

#### 1.1 工作流开始记录
```python
# 记录工作流开始
await execution_logger.log_workflow_start(
    trace_id=trace_id,
    step="sse_stream",
    message="SSE流式路线图生成开始",
    details={
        "user_id": request.user_id,
        "learning_goal": request.preferences.learning_goal,
        "include_tutorials": include_tutorials,
    }
)
```

#### 1.2 需求分析步骤记录
- **开始记录**：在调用 `intent_analyzer.analyze_stream()` 之前
- **完成记录**：在收到 `type="complete"` 事件后，记录：
  - roadmap_id
  - key_technologies（前5个）
  - difficulty_profile
  - parsed_goal
  - 执行耗时（duration_ms）
- **错误记录**：在收到 `type="error"` 事件后

#### 1.3 课程架构设计步骤记录
- **开始记录**：在调用 `architect.design_stream()` 之前
- **完成记录**：在收到 `type="complete"` 事件后，记录：
  - roadmap_id
  - title
  - stages_count
  - total_hours
  - completion_weeks
  - 执行耗时（duration_ms）
- **错误记录**：在收到 `type="error"` 事件后

#### 1.4 教程生成步骤记录
- **开始记录**：在调用 `_generate_tutorials_batch_stream()` 之前
- **完成记录**：在教程批次生成完成后，记录：
  - tutorials_count
  - summary
  - 执行耗时（duration_ms）

#### 1.5 数据库保存步骤记录
- **开始记录**：在开始保存到数据库之前
- **完成记录**：在数据库事务提交后，记录：
  - tutorials_count
  - 执行耗时（duration_ms）
- **错误记录**：捕获数据库保存异常

#### 1.6 整体流程完成记录
```python
# 记录整个流程完成
await execution_logger.log_workflow_complete(
    trace_id=trace_id,
    step="sse_stream",
    message="SSE流式路线图生成完成",
    roadmap_id=done_event.get("roadmap_id"),
    details={
        "include_tutorials": include_tutorials,
        "tutorials_count": len(tutorial_refs),
    }
)
```

#### 1.7 异常处理记录
```python
# 记录流程失败到execution_logs
await execution_logger.log_error(
    trace_id=trace_id,
    category="workflow",
    message=f"SSE流式路线图生成失败: {str(e)}",
    step="sse_stream",
    details={
        "error_type": type(e).__name__,
        "error": str(e),
    }
)
```

### 2. 增强 compact_roadmap_parse_error 错误处理

**文件**: `backend/app/agents/curriculum_architect.py` - `_parse_compact_roadmap()` 函数

#### 2.1 改进正则表达式容错性
支持中英文括号和小时标记的多种格式：

**Stage 解析**：
```python
# 原来：只支持中文括号
match = re.match(r'Stage\s+(\d+):\s*([^（]+)（([^）]+)）\[([0-9.]+)小时\]', line_stripped)

# 改进：支持中英文括号和多种小时标记
match = re.match(r'Stage\s+(\d+):\s*([^（(]+)[（(]([^）)]+)[）)]\[([0-9.]+)(?:小时|hours?)\]', line_stripped, re.IGNORECASE)
```

**Module 解析**：
```python
# 原来：只支持中文括号
match = re.match(r'Module\s+\d+\.(\d+):\s*([^（]+)（([^）]+)）', line_stripped)

# 改进：支持中英文括号
match = re.match(r'Module\s+\d+\.(\d+):\s*([^（(]+)[（(]([^）)]+)[）)]', line_stripped)
```

**Concept 解析**：
```python
# 原来：只支持中文括号
match = re.match(r'-\s*Concept:\s*([^（]+)（([^）]+)）\[([0-9.]+)小时\]', line_stripped)

# 改进：支持中英文括号和多种小时标记
match = re.match(r'-\s*Concept:\s*([^（(]+)[（(]([^）)]+)[）)]\[([0-9.]+)(?:小时|hours?)\]', line_stripped, re.IGNORECASE)
```

#### 2.2 增强错误日志记录
```python
except Exception as e:
    # 详细记录解析错误，包括完整内容和具体的错误位置
    logger.error(
        "compact_roadmap_parse_error",
        error=str(e),
        error_type=type(e).__name__,
        content_preview=content[:500],
        content_length=len(content),
        has_start_marker=start_marker in content if 'start_marker' in locals() else False,
        has_end_marker=end_marker in content if 'end_marker' in locals() else False,
        stages_parsed=len(stages) if 'stages' in locals() else 0,
    )
    raise ValueError(f"无法解析简洁格式的路线图: {e}")
```

#### 2.3 增强解析失败时的警告日志
为每个解析失败的行添加更详细的上下文：
```python
if not match:
    logger.warning("stage_parse_failed", line=line_stripped, line_length=len(line_stripped))
    continue
```

### 3. 改进 design_stream 错误处理

**文件**: `backend/app/agents/curriculum_architect.py` - `design_stream()` 方法

在错误事件中添加更多诊断信息：
```python
except ValueError as e:
    error_msg = f"LLM 输出格式解析失败: {str(e)}"
    logger.error(
        "curriculum_design_stream_parse_error",
        error=str(e),
        content_length=len(full_content) if 'full_content' in locals() else 0,
        content_preview=full_content[:500] + "..." if 'full_content' in locals() and len(full_content) > 500 else full_content if 'full_content' in locals() else "",
    )
    
    yield {
        "type": "error",
        "error": f"{error_msg}\n请检查是否超出 token 限制或格式不正确",
        "agent": "curriculum_architect",
        "details": {
            "error_type": "parse_error",
            "content_preview": full_content[:500] if 'full_content' in locals() else "",
        }
    }
```

## 修复效果

### 1. execution_logs 表记录完整性
现在 `roadmap.public.execution_logs` 表会记录以下步骤：

| step | category | level | agent_name | 说明 |
|------|----------|-------|------------|------|
| sse_stream | workflow | info | - | SSE流式路线图生成开始 |
| intent_analysis | workflow | info | IntentAnalyzer | 需求分析开始 |
| intent_analysis | workflow | info | IntentAnalyzer | 需求分析完成（含详细结果） |
| curriculum_design | workflow | info | CurriculumArchitect | 课程架构设计开始 |
| curriculum_design | workflow | info | CurriculumArchitect | 课程架构设计完成（含架构图） |
| tutorial_generation | workflow | info | TutorialGenerator | 批量教程生成开始 |
| tutorial_generation | workflow | info | TutorialGenerator | 批量教程生成完成 |
| database_save | workflow | info | - | 保存到数据库开始 |
| database_save | workflow | info | - | 保存到数据库完成 |
| sse_stream | workflow | info | - | SSE流式路线图生成完成 |

### 2. 错误可追溯性提升
- 所有错误都会记录到 execution_logs，包括：
  - 错误类型（error_type）
  - 错误消息（message）
  - 错误详情（details）
  - 所属步骤（step）
  - 所属分类（category）

### 3. 解析器容错性增强
- 支持中英文括号混用
- 支持多种小时标记格式（小时、hour、hours）
- 大小写不敏感
- 解析失败时提供更详细的诊断信息

## 测试建议

### 1. 测试 SSE 流式接口
```bash
# 发起流式路线图生成请求
curl -X POST http://localhost:8000/api/v1/roadmaps/generate-stream \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "preferences": {
      "learning_goal": "学习 Python Web 开发",
      "available_hours_per_week": 10,
      "current_level": "beginner",
      "career_background": "学生",
      "motivation": "提升技能",
      "content_preference": ["text", "video"]
    }
  }'
```

### 2. 检查 execution_logs
```sql
-- 查看最近的执行日志
SELECT 
    trace_id,
    step,
    level,
    message,
    duration_ms,
    created_at
FROM execution_logs
WHERE trace_id = '<your_trace_id>'
ORDER BY created_at;

-- 统计各步骤的执行情况
SELECT 
    step,
    COUNT(*) as count,
    AVG(duration_ms) as avg_duration_ms
FROM execution_logs
WHERE level = 'info'
GROUP BY step;

-- 查看错误日志
SELECT 
    trace_id,
    step,
    message,
    details,
    created_at
FROM execution_logs
WHERE level = 'error'
ORDER BY created_at DESC
LIMIT 10;
```

### 3. 测试解析器容错性
创建包含不同格式的测试用例：
- 中文括号 + 中文小时标记
- 英文括号 + 英文小时标记
- 混合格式
- 大小写变体

## 相关文件

- `backend/app/api/v1/roadmap.py` - SSE 流式接口
  - Line 962: `generate_full_roadmap_stream()` - 前端调用的端点
  - Line 490: `_generate_sse_stream()` - 核心流式生成函数（已修复）
- `backend/app/agents/curriculum_architect.py` - 课程架构师 Agent（已增强容错）
- `backend/app/services/execution_logger.py` - 执行日志服务
- `backend/app/models/database.py` - 数据库模型（execution_logs 表）
- `frontend-next/lib/api/endpoints.ts` - 前端 API 调用（Line 400-420）

## 注意事项

1. **性能影响**：每个步骤都会写入数据库，对于高并发场景需要监控数据库写入性能
2. **日志量**：execution_logs 表会快速增长，建议定期归档或清理旧数据
3. **trace_id 生成**：确保每个请求都有唯一的 trace_id 用于追踪
4. **错误处理**：execution_logger 写入失败不应影响主流程，已经做了异常捕获

## 后续优化建议

1. **批量写入优化**：考虑将 execution_logs 写入改为批量提交，减少数据库交互次数
2. **日志级别配置**：添加环境变量控制是否记录 debug 级别日志
3. **日志存储优化**：对于大型 details 字段，考虑压缩或外部存储
4. **监控告警**：基于 execution_logs 建立监控和告警机制
5. **性能分析**：利用 duration_ms 字段分析各步骤性能瓶颈

