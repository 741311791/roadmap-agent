# 任务执行日志系统 - 快速参考

## 🚀 快速开始

### 后端：添加新的日志类型

1. **在Runner中添加日志**:
```python
from app.services.execution_logger import execution_logger, LogCategory

await execution_logger.info(
    task_id=task_id,
    category=LogCategory.AGENT,  # 或 WORKFLOW
    step="your_step_name",
    agent_name="YourAgent",  # 可选
    roadmap_id=roadmap_id,  # 可选
    concept_id=concept_id,  # 可选
    message="User-friendly message",
    details={
        "log_type": "your_custom_log_type",  # 必需！
        "your_data": {...},
    },
    duration_ms=duration_ms,  # 可选
)
```

2. **选择合适的日志级别**:
- `execution_logger.info()` - 正常信息
- `execution_logger.warning()` - 警告
- `execution_logger.error()` - 错误

### 前端：添加新的卡片组件

1. **创建卡片组件** (`frontend-next/components/task/log-cards/your-card.tsx`):
```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface YourCardProps {
  details: {
    your_data: any;
  };
}

export function YourCard({ details }: YourCardProps) {
  return (
    <Card className="border-blue-200 bg-blue-50/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm">Your Title</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Your content */}
      </CardContent>
    </Card>
  );
}
```

2. **注册到LogCardRouter** (`frontend-next/components/task/log-cards/index.tsx`):
```tsx
import { YourCard } from './your-card';

export function LogCardRouter({ log }: LogCardRouterProps) {
  const logType = log.details?.log_type;

  // 添加你的路由
  if (logType === 'your_custom_log_type') {
    return <YourCard details={log.details} />;
  }

  // ... 其他路由
}

// 导出你的组件
export { YourCard } from './your-card';
```

---

## 📋 现有日志类型速查表

| log_type | 阶段 | 卡片组件 | 用途 |
|----------|------|----------|------|
| `intent_analysis_output` | Intent Analysis | `IntentAnalysisCard` | 展示AI对用户需求的理解 |
| `curriculum_design_output` | Curriculum Design | `CurriculumDesignCard` | 展示路线图结构设计 |
| `validation_passed` | Structure Validation | `ValidationResultCard` | 验证通过 |
| `validation_failed` | Structure Validation | `ValidationResultCard` | 验证失败 |
| `validation_skipped` | Structure Validation | `ValidationResultCard` | 跳过验证 |
| `review_waiting` | Human Review | `ReviewStatusCard` | 等待用户审核 |
| `review_approved` | Human Review | `ReviewStatusCard` | 用户批准 |
| `review_modification_requested` | Human Review | `ReviewStatusCard` | 用户请求修改 |
| `edit_completed` | Human Review | (默认展示) | 修改完成 |
| `content_generation_start` | Content Generation | `ContentProgressCard` | 开始生成概念内容 |
| `concept_completed` | Content Generation | `ContentProgressCard` | 概念内容生成完成 |
| `content_generation_failed` | Content Generation | `ContentProgressCard` | 概念内容生成失败 |
| `task_completed` | Finalizing | `TaskCompletedCard` | 任务完成 |

---

## 🎨 卡片设计规范

### 颜色主题

```tsx
// Intent Analysis - 蓝色
className="border-blue-200 bg-blue-50/50"

// Curriculum Design - 紫色
className="border-purple-200 bg-purple-50/50"

// Validation Passed - 绿色
className="border-green-200 bg-green-50/50"

// Validation Failed - 红色
className="border-red-200 bg-red-50/50"

// Review Waiting - 琥珀色
className="border-amber-200 bg-amber-50/50"

// Content Generation - 蓝色（进行中）/ 绿色（完成）
className="border-blue-200 bg-blue-50/50"
className="border-green-200 bg-green-50/50"

// Task Completed - 绿色渐变
className="border-green-300 bg-gradient-to-br from-green-50 to-emerald-50"
```

### 图标使用

```tsx
import {
  Lightbulb,      // Intent Analysis
  BookOpen,       // Curriculum Design
  CheckCircle2,   // Success / Validation Passed
  XCircle,        // Error / Validation Failed
  AlertTriangle,  // Warning
  Pause,          // Review Waiting
  Edit3,          // Modification
  Loader2,        // Loading / In Progress
  PartyPopper,    // Task Completed
} from 'lucide-react';
```

### 文本大小规范

```tsx
// 卡片标题
className="text-sm"

// 主要内容
className="text-sm text-foreground"

// 次要信息
className="text-xs text-muted-foreground"

// 超小文本（如时间戳、ID）
className="text-[10px] text-muted-foreground"
```

---

## 📊 数据结构示例

### Intent Analysis Output
```json
{
  "log_type": "intent_analysis_output",
  "output_summary": {
    "learning_goal": "Master React and build modern web apps",
    "key_technologies": ["React", "TypeScript", "Next.js"],
    "difficulty_level": "intermediate",
    "estimated_duration_weeks": 12,
    "estimated_hours_per_week": 10,
    "skill_gaps": [
      {
        "skill_name": "React Hooks",
        "current_level": "beginner",
        "required_level": "intermediate"
      }
    ],
    "learning_strategies": ["Build projects", "Read docs"]
  }
}
```

### Curriculum Design Output
```json
{
  "log_type": "curriculum_design_output",
  "output_summary": {
    "roadmap_id": "react-mastery-2024",
    "title": "React Mastery Roadmap",
    "total_stages": 4,
    "total_modules": 12,
    "total_concepts": 48,
    "total_hours": 120,
    "completion_weeks": 12,
    "stages": [
      {
        "name": "Fundamentals",
        "description": "Learn React basics...",
        "modules_count": 3,
        "estimated_hours": 30
      }
    ]
  }
}
```

### Content Generation Progress
```json
{
  "log_type": "concept_completed",
  "concept_id": "react-hooks-usestate",
  "concept_name": "useState Hook",
  "completed_content": ["tutorial", "resources", "quiz"],
  "content_summary": {
    "tutorial_chars": 5000,
    "resource_count": 5,
    "quiz_questions": 10
  },
  "total_duration_ms": 15000
}
```

### Task Completed
```json
{
  "log_type": "task_completed",
  "roadmap_id": "react-mastery-2024",
  "roadmap_url": "/roadmap/react-mastery-2024",
  "statistics": {
    "tutorials_generated": 45,
    "failed_concepts": 3
  },
  "next_actions": [
    {
      "action": "view_roadmap",
      "label": "View Roadmap",
      "url": "/roadmap/react-mastery-2024",
      "primary": true
    }
  ]
}
```

---

## 🔍 调试技巧

### 后端调试

1. **查看日志是否正确写入数据库**:
```sql
SELECT id, task_id, step, message, details->>'log_type' as log_type, created_at
FROM execution_logs
WHERE task_id = 'your-task-id'
ORDER BY created_at DESC;
```

2. **检查details字段结构**:
```sql
SELECT details
FROM execution_logs
WHERE details->>'log_type' = 'your_log_type'
LIMIT 1;
```

3. **查看某个阶段的所有日志**:
```sql
SELECT *
FROM execution_logs
WHERE task_id = 'your-task-id' AND step = 'content_generation'
ORDER BY created_at;
```

### 前端调试

1. **在浏览器控制台查看日志数据**:
```javascript
// 在TaskDetailPage中添加
console.log('Logs:', logs);
console.log('Log types:', logs.map(l => l.details?.log_type));
```

2. **检查LogCardRouter是否正确路由**:
```tsx
// 在LogCardRouter中添加
console.log('Routing log:', log.details?.log_type, log);
```

3. **验证卡片props**:
```tsx
// 在卡片组件中添加
console.log('Card props:', { outputSummary, details });
```

---

## 🚨 常见问题

### Q1: 日志写入了但前端不显示？

**检查清单**:
- [ ] `log_type` 字段是否存在？
- [ ] `log_type` 值是否正确？
- [ ] LogCardRouter中是否有对应的路由？
- [ ] WebSocket是否正常连接？
- [ ] 浏览器控制台是否有错误？

### Q2: 卡片显示不正确？

**检查清单**:
- [ ] `details`字段结构是否匹配卡片的props？
- [ ] 必需字段是否都存在？
- [ ] 数据类型是否正确（数字 vs 字符串）？
- [ ] 是否有TypeScript类型错误？

### Q3: 如何测试新的日志类型？

**步骤**:
1. 在后端添加日志记录代码
2. 触发相应的工作流阶段
3. 在数据库中验证日志已写入
4. 在前端任务详情页查看显示效果
5. 检查浏览器控制台是否有错误

---

## 📚 相关文档

- [完整实施总结](./TASK_EXECUTION_LOG_REFINEMENT_SUMMARY.md)
- [任务详情页文档](./frontend-next/docs/TASK_DETAIL_PAGE.md)
- [ExecutionLogger API文档](./backend/app/services/execution_logger.py)
- [LogCardRouter源码](./frontend-next/components/task/log-cards/index.tsx)

---

**最后更新**: 2025-12-13  
**维护者**: Development Team






