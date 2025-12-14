# Content Generation 日志展示设计方案

## 📋 需求分析

### 用户需求
1. **一目了然**：清楚看到有哪些内容需要生成
2. **状态明确**：每个内容的生成状态（成功/失败/生成中）
3. **错误可见**：失败时显示错误原因
4. **按需刷新**：不依赖 WebSocket，通过刷新按钮更新状态

### 技术约束
- 不使用 WebSocket 实时订阅 Concept 状态
- 通过 API 获取执行日志（`GET /api/v1/tasks/{task_id}/logs`）
- 从日志中提取内容生成相关信息

---

## 🎯 设计方案：三层分组卡片视图

### 核心思想
- **按路线图结构展示**：Stage -> Module -> Concept
- **状态聚合**：显示每个层级的统计信息
- **可折叠/展开**：减少信息过载
- **手动刷新**：用户主动刷新获取最新状态

---

## 🎨 UI 设计

### 整体布局

```
┌─────────────────────────────────────────────────────────────────┐
│ Content Generation Overview          [↻ Refresh Status]         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│ ┌── Stage 1: Fundamentals ─────────────────────────────────────┐│
│ │ 📊 Progress: 5/6 concepts • 1 failed                         ││
│ │                                                               ││
│ │ ▼ Module 1.1: Basic Techniques                               ││
│ │   ├─ ✅ Grip and Hold       [Tutorial] [Resources] [Quiz]    ││
│ │   ├─ ✅ Footwork Basics     [Tutorial] [Resources] [Quiz]    ││
│ │   └─ ❌ Serving Mechanics   Error: Content policy violation  ││
│ │                              [Retry]                          ││
│ │                                                               ││
│ │ ▼ Module 1.2: Court Awareness                                ││
│ │   ├─ ✅ Positioning         [Tutorial] [Resources] [Quiz]    ││
│ │   └─ ✅ Movement Patterns   [Tutorial] [Resources] [Quiz]    ││
│ └───────────────────────────────────────────────────────────────┘│
│                                                                  │
│ ┌── Stage 2: Advanced Skills ───────────────────────────────────┐│
│ │ 📊 Progress: 8/9 concepts • 1 failed                         ││
│ │                                                               ││
│ │ ▼ Module 2.1: Advanced Strokes                               ││
│ │   ├─ ✅ Smash Technique     [Tutorial] [Resources] [Quiz]    ││
│ │   ├─ ✅ Drop Shot           [Tutorial] [Resources] [Quiz]    ││
│ │   └─ ❌ Net Play            Error: API timeout               ││
│ │                              [Retry]                          ││
│ │   ...                                                         ││
│ └───────────────────────────────────────────────────────────────┘│
│                                                                  │
│ Last updated: 2 minutes ago                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 数据结构设计

### 1. 从执行日志提取内容生成信息

```typescript
interface ConceptGenerationStatus {
  concept_id: string;
  concept_name: string;
  
  // 三种内容类型的状态
  tutorial: {
    status: 'pending' | 'generating' | 'completed' | 'failed';
    error?: string;
    tutorial_id?: string;
    content_url?: string;
  };
  
  resources: {
    status: 'pending' | 'generating' | 'completed' | 'failed';
    error?: string;
    resources_id?: string;
    resources_count?: number;
  };
  
  quiz: {
    status: 'pending' | 'generating' | 'completed' | 'failed';
    error?: string;
    quiz_id?: string;
    questions_count?: number;
  };
}

interface ModuleGenerationStatus {
  module_id: string;
  module_name: string;
  concepts: ConceptGenerationStatus[];
  
  // 统计信息
  total_concepts: number;
  completed_concepts: number;
  failed_concepts: number;
}

interface StageGenerationStatus {
  stage_id: string;
  stage_name: string;
  modules: ModuleGenerationStatus[];
  
  // 统计信息
  total_concepts: number;
  completed_concepts: number;
  failed_concepts: number;
}

interface ContentGenerationOverview {
  stages: StageGenerationStatus[];
  last_updated: string;
  
  // 全局统计
  total_concepts: number;
  completed_concepts: number;
  failed_concepts: number;
  progress_percentage: number;
}
```

### 2. 日志解析逻辑

```typescript
/**
 * 从执行日志中提取内容生成状态
 */
function parseContentGenerationStatus(
  logs: ExecutionLog[],
  roadmapFramework: RoadmapFramework
): ContentGenerationOverview {
  // 1. 按 log_type 分类日志
  const tutorialLogs = logs.filter(log => 
    log.details?.log_type === 'tutorial_generation_completed' ||
    log.details?.log_type === 'tutorial_generation_failed'
  );
  
  const resourceLogs = logs.filter(log => 
    log.details?.log_type === 'resource_generation_completed' ||
    log.details?.log_type === 'resource_generation_failed'
  );
  
  const quizLogs = logs.filter(log => 
    log.details?.log_type === 'quiz_generation_completed' ||
    log.details?.log_type === 'quiz_generation_failed'
  );
  
  // 2. 构建 concept_id -> status 映射
  const conceptStatusMap = new Map<string, ConceptGenerationStatus>();
  
  for (const stage of roadmapFramework.stages) {
    for (const module of stage.modules) {
      for (const concept of module.concepts) {
        // 初始化状态
        conceptStatusMap.set(concept.concept_id, {
          concept_id: concept.concept_id,
          concept_name: concept.name,
          tutorial: { status: 'pending' },
          resources: { status: 'pending' },
          quiz: { status: 'pending' },
        });
        
        // 从日志中更新状态
        updateConceptStatusFromLogs(
          conceptStatusMap.get(concept.concept_id)!,
          tutorialLogs,
          resourceLogs,
          quizLogs
        );
      }
    }
  }
  
  // 3. 重新组织为分层结构
  return buildHierarchicalStatus(roadmapFramework, conceptStatusMap);
}

/**
 * 根据日志更新概念状态
 */
function updateConceptStatusFromLogs(
  status: ConceptGenerationStatus,
  tutorialLogs: ExecutionLog[],
  resourceLogs: ExecutionLog[],
  quizLogs: ExecutionLog[]
) {
  const conceptId = status.concept_id;
  
  // 更新 Tutorial 状态
  const tutorialLog = tutorialLogs.find(log => 
    log.details?.concept_id === conceptId
  );
  if (tutorialLog) {
    if (tutorialLog.details?.log_type === 'tutorial_generation_completed') {
      status.tutorial = {
        status: 'completed',
        tutorial_id: tutorialLog.details.tutorial_id,
        content_url: tutorialLog.details.content_url,
      };
    } else {
      status.tutorial = {
        status: 'failed',
        error: tutorialLog.details?.error || 'Unknown error',
      };
    }
  }
  
  // 更新 Resources 状态（类似逻辑）
  // 更新 Quiz 状态（类似逻辑）
}
```

---

## 🎨 UI 组件设计

### 1. ContentGenerationOverview（主容器）

```typescript
interface ContentGenerationOverviewProps {
  taskId: string;
  roadmapId: string;
  initialLogs: ExecutionLog[];
}

export function ContentGenerationOverview({
  taskId,
  roadmapId,
  initialLogs,
}: ContentGenerationOverviewProps) {
  const [logs, setLogs] = useState(initialLogs);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  
  // 获取路线图框架
  const { data: roadmap } = useRoadmap(roadmapId);
  
  // 解析内容生成状态
  const overview = useMemo(() => {
    if (!roadmap) return null;
    return parseContentGenerationStatus(logs, roadmap.framework);
  }, [logs, roadmap]);
  
  // 刷新状态
  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      const logsData = await getTaskLogs(taskId);
      setLogs(logsData.logs || []);
      setLastUpdated(new Date());
    } catch (error) {
      console.error('Failed to refresh logs:', error);
    } finally {
      setIsRefreshing(false);
    }
  };
  
  if (!overview) {
    return <div>Loading...</div>;
  }
  
  return (
    <Card className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">Content Generation Overview</h3>
          <p className="text-sm text-muted-foreground mt-1">
            {overview.completed_concepts}/{overview.total_concepts} concepts completed
            {overview.failed_concepts > 0 && (
              <span className="text-red-600 ml-2">
                • {overview.failed_concepts} failed
              </span>
            )}
          </p>
        </div>
        
        <Button
          onClick={handleRefresh}
          disabled={isRefreshing}
          variant="outline"
          size="sm"
        >
          {isRefreshing ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Refreshing...
            </>
          ) : (
            <>
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh Status
            </>
          )}
        </Button>
      </div>
      
      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex items-center justify-between text-sm mb-2">
          <span>Overall Progress</span>
          <span className="font-medium">{overview.progress_percentage}%</span>
        </div>
        <Progress value={overview.progress_percentage} />
      </div>
      
      {/* Stages */}
      <div className="space-y-4">
        {overview.stages.map((stage) => (
          <StageAccordion key={stage.stage_id} stage={stage} />
        ))}
      </div>
      
      {/* Last Updated */}
      <div className="mt-6 pt-4 border-t text-xs text-muted-foreground text-right">
        Last updated: {formatRelativeTime(lastUpdated)}
      </div>
    </Card>
  );
}
```

### 2. StageAccordion（Stage 折叠面板）

```typescript
interface StageAccordionProps {
  stage: StageGenerationStatus;
}

function StageAccordion({ stage }: StageAccordionProps) {
  const [isOpen, setIsOpen] = useState(true);
  
  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Stage Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-4 py-3 bg-muted/50 hover:bg-muted/70 flex items-center justify-between transition-colors"
      >
        <div className="flex items-center gap-3">
          {isOpen ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
          <h4 className="font-medium">{stage.stage_name}</h4>
        </div>
        
        <div className="flex items-center gap-3 text-sm">
          <Badge variant="outline">
            {stage.completed_concepts}/{stage.total_concepts} concepts
          </Badge>
          {stage.failed_concepts > 0 && (
            <Badge variant="destructive">
              {stage.failed_concepts} failed
            </Badge>
          )}
          <Progress 
            value={(stage.completed_concepts / stage.total_concepts) * 100} 
            className="w-24"
          />
        </div>
      </button>
      
      {/* Modules */}
      {isOpen && (
        <div className="p-4 space-y-3">
          {stage.modules.map((module) => (
            <ModuleSection key={module.module_id} module={module} />
          ))}
        </div>
      )}
    </div>
  );
}
```

### 3. ModuleSection（Module 列表）

```typescript
interface ModuleSectionProps {
  module: ModuleGenerationStatus;
}

function ModuleSection({ module }: ModuleSectionProps) {
  return (
    <div className="border-l-2 border-sage-200 pl-4">
      {/* Module Header */}
      <div className="flex items-center justify-between mb-2">
        <h5 className="text-sm font-medium text-muted-foreground">
          {module.module_name}
        </h5>
        <span className="text-xs text-muted-foreground">
          {module.completed_concepts}/{module.total_concepts}
        </span>
      </div>
      
      {/* Concepts */}
      <div className="space-y-2">
        {module.concepts.map((concept) => (
          <ConceptStatusCard key={concept.concept_id} concept={concept} />
        ))}
      </div>
    </div>
  );
}
```

### 4. ConceptStatusCard（Concept 状态卡片）

```typescript
interface ConceptStatusCardProps {
  concept: ConceptGenerationStatus;
}

function ConceptStatusCard({ concept }: ConceptStatusCardProps) {
  const hasFailure = 
    concept.tutorial.status === 'failed' ||
    concept.resources.status === 'failed' ||
    concept.quiz.status === 'failed';
  
  const allCompleted = 
    concept.tutorial.status === 'completed' &&
    concept.resources.status === 'completed' &&
    concept.quiz.status === 'completed';
  
  return (
    <div
      className={cn(
        'flex items-center justify-between p-3 rounded-md border transition-colors',
        allCompleted && 'bg-green-50/50 border-green-200',
        hasFailure && 'bg-red-50/50 border-red-200',
        !allCompleted && !hasFailure && 'bg-muted/30'
      )}
    >
      {/* Left: Concept Name & Status Icon */}
      <div className="flex items-center gap-2">
        {allCompleted && <CheckCircle2 className="w-4 h-4 text-green-600" />}
        {hasFailure && <XCircle className="w-4 h-4 text-red-600" />}
        {!allCompleted && !hasFailure && <Loader2 className="w-4 h-4 text-blue-600 animate-spin" />}
        
        <span className="text-sm font-medium">{concept.concept_name}</span>
      </div>
      
      {/* Right: Content Type Badges */}
      <div className="flex items-center gap-2">
        <ContentTypeBadge label="Tutorial" status={concept.tutorial.status} />
        <ContentTypeBadge label="Resources" status={concept.resources.status} />
        <ContentTypeBadge label="Quiz" status={concept.quiz.status} />
        
        {/* Retry Button (if failed) */}
        {hasFailure && (
          <Button size="sm" variant="ghost" className="h-7 px-2">
            <RefreshCw className="w-3 h-3" />
          </Button>
        )}
      </div>
      
      {/* Error Message (if any) */}
      {hasFailure && (
        <div className="col-span-2 mt-2 pt-2 border-t border-red-200">
          <p className="text-xs text-red-700">
            {concept.tutorial.error || concept.resources.error || concept.quiz.error}
          </p>
        </div>
      )}
    </div>
  );
}
```

### 5. ContentTypeBadge（内容类型状态标记）

```typescript
interface ContentTypeBadgeProps {
  label: string;
  status: 'pending' | 'generating' | 'completed' | 'failed';
}

function ContentTypeBadge({ label, status }: ContentTypeBadgeProps) {
  const config = {
    pending: { icon: Clock, className: 'bg-gray-100 text-gray-600' },
    generating: { icon: Loader2, className: 'bg-blue-100 text-blue-600 animate-pulse' },
    completed: { icon: CheckCircle2, className: 'bg-green-100 text-green-600' },
    failed: { icon: XCircle, className: 'bg-red-100 text-red-600' },
  }[status];
  
  const Icon = config.icon;
  
  return (
    <Badge variant="outline" className={cn('text-xs gap-1', config.className)}>
      <Icon className={cn('w-3 h-3', status === 'generating' && 'animate-spin')} />
      {label}
    </Badge>
  );
}
```

---

## 🔄 刷新机制设计

### 1. 手动刷新

```typescript
// 用户点击 "Refresh Status" 按钮
const handleRefresh = async () => {
  setIsRefreshing(true);
  try {
    // 1. 重新获取执行日志
    const logsData = await getTaskLogs(taskId);
    setLogs(logsData.logs || []);
    
    // 2. 重新解析内容生成状态
    const newOverview = parseContentGenerationStatus(logsData.logs, roadmap.framework);
    
    // 3. 更新时间戳
    setLastUpdated(new Date());
    
    toast.success('Status refreshed successfully');
  } catch (error) {
    toast.error('Failed to refresh status');
  } finally {
    setIsRefreshing(false);
  }
};
```

### 2. 自动刷新（可选）

```typescript
// 如果任务状态仍为 processing，可以启用自动刷新
useEffect(() => {
  if (taskStatus !== 'processing') return;
  
  const interval = setInterval(() => {
    handleRefresh();
  }, 30000); // 每30秒刷新一次
  
  return () => clearInterval(interval);
}, [taskStatus]);
```

---

## 📦 集成到 TaskDetail 页面

### 修改 TaskDetail 页面

```typescript
export default function TaskDetailPage() {
  // ... 现有代码 ...
  
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card/50 backdrop-blur-sm sticky top-0 z-10">
        {/* ... 现有 header 代码 ... */}
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Horizontal Stepper */}
        <HorizontalWorkflowStepper
          currentStep={taskInfo.current_step}
          status={taskInfo.status}
          selectedPhase={selectedPhaseFilter || undefined}
          onPhaseSelect={(phaseId) => {
            setSelectedPhaseFilter(selectedPhaseFilter === phaseId ? null : phaseId);
          }}
        />

        {/* ✅ 新增：Content Generation 专属视图 */}
        {selectedPhaseFilter === 'content_generation' && taskInfo.roadmap_id && (
          <ContentGenerationOverview
            taskId={taskId}
            roadmapId={taskInfo.roadmap_id}
            initialLogs={executionLogs}
          />
        )}

        {/* 原有的 Execution Logs Timeline（其他阶段使用） */}
        {selectedPhaseFilter !== 'content_generation' && (
          <ExecutionLogTimeline
            logs={executionLogs}
            selectedPhaseFilter={selectedPhaseFilter}
            taskStatus={taskInfo.status}
            roadmapId={taskInfo.roadmap_id}
            taskTitle={taskInfo.title}
            onShowAllLogs={() => setSelectedPhaseFilter(null)}
          />
        )}

        {/* Error Message (if failed) */}
        {/* ... 现有错误处理代码 ... */}
      </div>
    </div>
  );
}
```

---

## 🎯 设计优势

### 1. **结构化展示**
- 按照路线图的三层结构（Stage -> Module -> Concept）组织
- 用户能清楚看到整个路线图的内容生成情况

### 2. **信息层次清晰**
- Stage 级别：总览统计
- Module 级别：分组展示
- Concept 级别：详细状态

### 3. **状态可视化**
- 颜色编码：绿色（成功）、红色（失败）、蓝色（进行中）、灰色（待处理）
- 图标辅助：✅ ❌ ⏳ 🔄
- 进度条：直观展示完成度

### 4. **错误信息透明**
- 失败的概念直接显示错误原因
- 提供重试按钮

### 5. **性能优化**
- 不依赖 WebSocket（避免长连接开销）
- 按需刷新（用户主动控制）
- 可折叠面板（减少初始渲染）

---

## 📝 实现计划

### Phase 1: 数据层（1-2小时）
1. ✅ 定义 TypeScript 接口
2. ✅ 实现日志解析函数 `parseContentGenerationStatus`
3. ✅ 添加单元测试

### Phase 2: UI 组件（2-3小时）
1. ✅ 实现 `ContentGenerationOverview` 主容器
2. ✅ 实现 `StageAccordion` 折叠面板
3. ✅ 实现 `ModuleSection` 模块列表
4. ✅ 实现 `ConceptStatusCard` 状态卡片
5. ✅ 实现 `ContentTypeBadge` 标记组件

### Phase 3: 集成（1小时）
1. ✅ 修改 `TaskDetailPage`，添加条件渲染
2. ✅ 测试交互流程
3. ✅ 优化样式和动画

---

## 🎨 视觉效果预览

### 成功的 Concept

```
┌────────────────────────────────────────────────────────────┐
│ ✅ Grip and Hold           [✅ Tutorial] [✅ Resources] [✅ Quiz] │
└────────────────────────────────────────────────────────────┘
```

### 失败的 Concept

```
┌────────────────────────────────────────────────────────────┐
│ ❌ Serving Mechanics       [❌ Tutorial] [✅ Resources] [✅ Quiz] │
│                                                            │
│ Error: Input data may contain inappropriate content       │
│ [🔄 Retry]                                                 │
└────────────────────────────────────────────────────────────┘
```

### 生成中的 Concept

```
┌────────────────────────────────────────────────────────────┐
│ ⏳ Footwork Basics        [⏳ Tutorial] [⏳ Resources] [⏳ Quiz] │
└────────────────────────────────────────────────────────────┘
```

---

## 🚀 后续优化建议

### 1. 批量重试
- 在 Stage 或 Module 级别添加"Retry All Failed"按钮

### 2. 导出报告
- 生成 Content Generation Summary（PDF/JSON）

### 3. 实时进度（可选）
- 如果未来需要实时进度，可以在组件内部启用轮询

### 4. 过滤和搜索
- 按状态过滤（只显示失败的）
- 按概念名称搜索

---

## 总结

这个设计方案的核心优势：
1. ✅ **结构化**：完全遵循路线图的三层架构
2. ✅ **直观**：用户一眼能看到所有概念的状态
3. ✅ **可控**：手动刷新，用户掌控数据更新时机
4. ✅ **可扩展**：易于添加批量操作、过滤等功能
5. ✅ **性能好**：不依赖 WebSocket，按需加载

这个方案完美契合你的需求：让用户一目了然地知道都会生成哪些 Content 以及各个 Content 的状态日志。
