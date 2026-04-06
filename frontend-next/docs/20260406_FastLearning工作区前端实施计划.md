# FastLearning Workspace（学习空间）— 前端实施计划（基于 demo 重写版）

## 一、文档信息

| 项 | 内容 |
|----|------|
| 范围 | `frontend-next` 前端重构 |
| 设计来源 | `best-practice/fastlearning-ai` demo + 当前 DeerFlow 测试页能力 |
| 重构目标 | 从「聊天测试页」升级为「Workspace 学习空间」 |
| 日期 | 2026-04-06 |

---

## 二、重写背景与结论

本次文档已根据 `best-practice/fastlearning-ai` demo 重新梳理，不再只停留在抽象的「左脑 / 右脑」概念，而是明确落到：

1. **页面级设计**：Hub、路线图工作区、章节学习工作区、Artifact 预览态。  
2. **用户动线**：从新建学习、恢复学习，到章节级对话、资源收集、预览切换的完整闭环。  
3. **真实数据复用**：`RoadmapFramework`、教程、资源、Quiz 等直接接现有 API，不再把路线图主体当作 mock 数据。  
4. **开源复用**：优先使用现有依赖与现成能力，不重复造轮子。

**最重要的调整**：

- 不再把右脑路线图定义成一个完全自定义 JSON 结构。  
- `Roadmap Framework` 直接复用现有类型与接口：
  - `RoadmapFramework`
  - `Stage`
  - `Module`
  - `Concept`
- 章节正文、资源、测验也不再写成 mock-only 方案，而是直接对接：
  - `useRoadmap`
  - `roadmapsApi.getById`
  - `contentApi.getTutorial`
  - `contentApi.getResources`
  - `contentApi.getQuiz`

---

## 三、demo 项目逆向分析

### 3.1 demo 的核心页面状态

`best-practice/fastlearning-ai/src/App.tsx` 里实际定义了 4 个页面状态：

```text
hub -> roadmap -> learning -> preview
```

这 4 个状态与我们期望的 Workspace 四阶段几乎一一对应：

| demo 状态 | 对应 FastLearning 阶段 | 含义 |
|----------|------------------------|------|
| `hub` | 第一阶段：全局入口与分流 | 新建学习 + 恢复学习 |
| `roadmap` | 第二阶段：路线图工作区 | 左侧 Copilot，右侧路线图 |
| `learning` | 第三阶段：沉浸学习 | 左侧 Copilot，右侧章节内容 |
| `preview` | 第四阶段：资源预览 | 画布被 Artifact 预览接管 |

### 3.2 demo 的关键功能模块

从 `src/App.tsx`、`HubView.tsx`、`Copilot.tsx`、`RoadmapView.tsx`、`ContentView.tsx`、`ArtifactPreview.tsx` 可归纳出以下模块：

1. **HubView**
   - 中央大输入框
   - 推荐标签
   - 历史 Workspace 卡片
   - 点击历史卡片恢复学习

2. **Copilot**
   - 固定左栏
   - 当前上下文对应的聊天会话
   - 按 `targetId` 切换会话
   - 聊天历史下拉
   - Artifact 卡片 / Quiz 卡片内嵌消息流

3. **RoadmapView**
   - 右侧路线图画布
   - 层级树展示
   - 节点完成 / 进行中 / 未开始状态
   - 点击节点进入内容学习

4. **ContentView**
   - 顶部章节 Header
   - 章节正文 Markdown
   - 代码块
   - 章节级多模态生成按钮
   - 章节级 Material Collector

5. **ArtifactPreview**
   - 全屏预览态
   - 支持 Markdown / PPT / Mindmap / 媒体预览 mock
   - 可从学习态返回

6. **Vault Drawer**
   - 全局资源抽屉
   - 汇总当前 Workspace 下所有 Artifact
   - 从右上角侧滑进入

### 3.3 demo 的 UI 设计特征

这个 demo 的设计不是传统「聊天在中间，附件在右边」，而是：

1. **极窄全局图标栏**
   - 只负责全局导航和 Resource Vault 入口

2. **固定宽度 Copilot 左栏**
   - 宽度稳定，承担上下文问答与会话切换
   - 不抢占主画布

3. **右侧主画布是唯一主视觉**
   - 路线图、正文、预览都在这里切换
   - 用户注意力始终集中在右脑

4. **会话按目标切分**
   - 路线图有路线图聊天
   - 每个章节有自己的章节聊天
   - 这是 demo 非常关键、也非常值得复用的设计

### 3.4 demo 最值得复用的交互思想

1. **Workspace 是一级对象，不是 thread 的附属概念**  
2. **Copilot 与画布强绑定，但不混在一起**  
3. **聊天历史按目标上下文切换，而不是只有一条全局长会话**  
4. **章节工具条放在内容 Header，而不是塞进聊天输入框**  
5. **Artifact 既能在聊天里以卡片出现，也能进入资源库，还能劫持主画布预览**

---

## 四、对当前项目的重构原则

### 4.1 明确保留的现有能力

以下能力直接复用，不重写：

- `components/deerflow-chat-test/deerflow-chat-state.ts`
- `components/deerflow-chat-test/deerflow-standalone-api.ts`
- `components/deerflow-chat-test/deerflow-message-list*.tsx`
- `components/deerflow-chat-test/deerflow-input-box.tsx`
- `components/deerflow-chat-test/deerflow-artifact-detail.tsx`
- `components/markdown/rich-streamdown.tsx`
- `react-resizable-panels`
- `motion` / `framer-motion`
- `reactflow` + `dagre`

### 4.2 明确不再使用 mock 的数据

以下数据 **直接复用现有真实类型和 API**：

#### 1. 路线图框架

直接使用 `RoadmapFramework`：

- `roadmap_id`
- `title`
- `stages`
- `total_estimated_hours`
- `recommended_completion_weeks`

内部层级直接使用：

- `Stage.stage_id / name / description / order / modules`
- `Module.module_id / name / description / concepts`
- `Concept.concept_id / name / description / estimated_hours / difficulty / prerequisites / tutorial_id / quiz_id / resources_count`

#### 2. 路线图获取

- `useRoadmap(roadmapId)`
- `roadmapsApi.getById(roadmapId)`

#### 3. 教程内容

- `contentApi.getTutorial(roadmapId, conceptId, version?)`
- `contentApi.getLatestTutorial(roadmapId, conceptId)`

#### 4. 学习资源

- `contentApi.getResources(roadmapId, conceptId)`

#### 5. 测验

- `contentApi.getQuiz(roadmapId, conceptId)`
- 通过学习接口提交答题结果（现有 learning API）

### 4.3 可以先保留 mock 的部分

以下部分若后端协议暂未对齐，可先做占位，但要明确是过渡层：

- DeerFlow 返回的 Artifact 元信息标准化
- 章节内「划线解释」的结构化上下文协议
- 章节级多模态生成结果的分类字段
- 章节级会话与全局 thread 的持久化映射关系

---

## 五、最终信息架构

### 5.1 一级页面状态

结合 demo 与现有系统，最终前端状态建议定义为：

```text
WorkspaceView:
  hub
  roadmap
  learning
  preview
```

### 5.2 二级上下文状态

```text
ConversationTarget:
  roadmap
  concept:{concept_id}

CanvasMode:
  roadmap_outline
  roadmap_graph
  chapter_reader
  artifact_preview
```

### 5.3 页面间转移

1. Hub 输入目标 → 创建 Workspace → 进入 `roadmap`
2. 在路线图里点击概念节点 → 进入 `learning`
3. 在内容页点预览或从资源库点开文件 → 进入 `preview`
4. 预览返回 → 回到 `learning` 或 `roadmap`
5. 任意时刻打开 Resource Vault → 不改变主页面状态，只打开抽屉

---

## 六、页面设计草图

以下草图用于指导布局，不代表最终视觉细节。

### 6.1 页面 A：Hub（新建 / 恢复学习）

**目标**：解决空白页恐惧，让用户在一个页面里完成「新建」和「恢复」。

```text
┌──────────────────────────────────────────────────────────────┐
│                        FastLearning                          │
│          今天想学点什么？或想开发什么产品？                 │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐   │
│   │  [ 搜索图标 ]  What do you want to learn today?      │   │
│   │                                              [Start] │   │
│   └──────────────────────────────────────────────────────┘   │
│                                                              │
│   [零基础写爬虫] [前端进阶] [Go 并发编程] [系统设计]         │
│                                                              │
│   Resume Learning                                            │
│   ┌────────────────────┐  ┌────────────────────┐            │
│   │ Go 并发编程        │  │ React 动效设计      │            │
│   │ progress 45%       │  │ progress 20%        │            │
│   └────────────────────┘  └────────────────────┘            │
└──────────────────────────────────────────────────────────────┘
```

**设计决策**：

- 直接复用 demo 的「中心 Hero + 历史卡片」。
- 历史列表不从 DeerFlow thread 直接裸渲染，而优先从路线图列表接口或 Workspace 聚合视图提供。
- 若暂时没有完整 Workspace 列表接口，可先用 `roadmapsApi.getMyRoadmaps()` + 本地 Workspace 元信息拼装。

### 6.2 页面 B：Roadmap Workspace（路线图工作区）

**目标**：让用户在路线图级别和 Copilot 协作，而不是把路线图塞进聊天流里。

```text
┌──────┬──────────────────────────────┬───────────────────────────────┐
│ 图标栏 │        Copilot 左栏           │         右脑画布：路线图         │
│      │                              │                               │
│ [Hub]│  标题：Roadmap Discussion     │  标题 / 概览统计 / 视图切换      │
│ [Vault]                              │  [Outline] [Graph]            │
│      │  消息流                       │                               │
│      │  - 用户提问                   │  Stage 1                      │
│      │  - AI 修改建议                │   Module A                    │
│      │  - 工具消息                   │    Concept 1                  │
│      │                               │    Concept 2                  │
│      │  输入框                       │                               │
│      │                               │  Stage 2 ...                  │
└──────┴──────────────────────────────┴───────────────────────────────┘
```

**设计决策**：

- 右侧路线图主体直接复用 `RoadmapFramework`，不重新发明 `RoadmapNode[]`。
- 首版支持两种视图：
  - `Knowledge Outline`：直接复用或扩展当前 `components/roadmap/roadmap-view.tsx`
  - `Knowledge Graph`：用 `reactflow` + `dagre` 基于 `stages/modules/concepts` 映射生成
- 左侧 Copilot 会话目标为 `roadmap`。

### 6.3 页面 C：Learning Workspace（章节学习工作区）

**目标**：进入概念后，右侧变成阅读和操作中心；左侧 Copilot 自动切换到章节语境。

```text
┌──────┬──────────────────────────────┬──────────────────────────────────┐
│ 图标栏 │       Copilot 左栏            │       右脑画布：章节正文            │
│      │                              │                                  │
│ [Hub]│ 标题：Chapter Discussion      │ ← 返回路线图   章节标题            │
│ [Vault]                              │ [MD] [PPT] [Map] [Video] [Audio] │
│      │ 会话历史（该章节）             │                          [资料夹] │
│      │ 消息流                         │                                  │
│      │ - 对章节提问                   │ Markdown 正文                     │
│      │ - Quiz 卡片                    │ 代码块                            │
│      │ - Artifact 卡片                │ 插图 / Mermaid / 高亮片段         │
│      │                                │                                  │
│      │ 输入框                         │ 底部触发 Quiz / 进度反馈          │
└──────┴──────────────────────────────┴──────────────────────────────────┘
```

**设计决策**：

- `currentTargetId` 从 `roadmap` 切为 `concept:{concept_id}`。
- 章节正文直接使用：
  - `contentApi.getTutorial(roadmapId, conceptId)`
  - `contentApi.getResources(roadmapId, conceptId)`
  - `contentApi.getQuiz(roadmapId, conceptId)`
- 章节级「资料夹」复用 demo 的 `Material Collector` 思路，但数据来源改为真实 Artifact / Resources。

### 6.4 页面 D：Artifact Preview（资源预览）

**目标**：主画布暂时被文件预览接管，但不破坏 Workspace 上下文。

```text
┌──────────────────────────────────────────────────────────────┐
│ ← 返回章节       [图标] Artifact 标题                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                 预览区域（HTML / PDF / PPT）                  │
│                                                              │
│      Markdown 预览 / iframe / PDF Viewer / PPT Viewer        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**设计决策**：

- DeerFlow HTML 类产物优先 `iframe + sandbox`。
- PDF 预览接成熟组件，不自研。
- Markdown 和纯文本可复用现有 Markdown 渲染链。

### 6.5 页面 E：Resource Vault（全局资源库抽屉）

```text
┌────────────────────────────────────────────┐
│ Resource Vault                          ×  │
├────────────────────────────────────────────┤
│ Workspace 下全部资源                       │
│                                            │
│ [PPT]  第 2 章复习 PPT              >      │
│ [Map]  并发模型思维导图             >      │
│ [PDF]  资料总结                     >      │
│ [URL]  推荐视频                     >      │
│                                            │
│ [批量下载]                                  │
└────────────────────────────────────────────┘
```

**设计决策**：

- 抽屉是全局层，不替代主画布。
- 点击条目默认进入 `preview`。
- 支持按章节筛选和全 Workspace 汇总两种模式。

---

## 七、真实数据复用方案

### 7.1 路线图：直接复用 `RoadmapFramework`

路线图画布不要再定义 demo 那种简单的：

```ts
{ title, nodes: RoadmapNode[] }
```

而是直接以现有 `RoadmapFramework` 作为单源真相。

#### 路线图 Outline 视图

直接复用或增强当前：

- `components/roadmap/roadmap-view.tsx`

它已经能渲染：

- stages
- modules
- concepts
- 统计信息

#### 路线图 Graph 视图

将 `RoadmapFramework` 转成 React Flow 数据：

- `Stage` → 一级 cluster / group
- `Module` → 二级节点
- `Concept` → 可点击叶子节点

可在前端新增转换器：

```text
RoadmapFramework -> GraphNode[] + GraphEdge[]
```

### 7.2 章节内容：直接复用教程接口

用户点击 Concept 后，不用 mock `LearningContent`，而是：

1. 从当前 `RoadmapFramework` 中定位 `concept_id`
2. 调 `contentApi.getTutorial(roadmapId, conceptId)`
3. 在右侧 `chapter-reader` 展示教程

### 7.3 资源与测验：直接复用内容接口

章节 Header 中的多模态按钮应拆成两类：

1. **已有资源读取**
   - `contentApi.getResources(roadmapId, conceptId)`
   - `contentApi.getQuiz(roadmapId, conceptId)`

2. **DeerFlow/Agent 额外生成**
   - PPT
   - 思维导图
   - 播客
   - 音频总结

也就是说：

- 教程、资源、Quiz 是主业务内容体系  
- DeerFlow 生成式产物是增强层

### 7.4 进度状态：来自 Concept 真实字段

demo 用 `todo / in-progress / completed` 自定义状态。

我们的系统应优先从以下真实字段推导：

- `content_status`
- `resources_status`
- `quiz_status`
- Quiz 提交记录

然后在 UI 层派生出：

- `not_started`
- `in_progress`
- `completed`

---

## 八、会话模型重构方案

demo 最有价值的一点，是 **会话按目标切分**。

### 8.1 推荐的前端会话模型

```text
Workspace
  ├─ roadmap conversation
  ├─ concept conversation: concept_id = A
  ├─ concept conversation: concept_id = B
  └─ ...
```

### 8.2 对当前 DeerFlow 测试页的落地方式

首版不一定立刻要求后端支持多 thread。

可分两步：

#### 第一步：前端 UI 先支持目标级会话切换

- 当前 thread 作为 Workspace 主容器
- 前端在 store 中维护 `conversation_target_id`
- 消息视图按 target 过滤或组织展示

#### 第二步：后端支持目标级 thread / session

- `roadmap` 一个会话
- 每个 `concept_id` 一个会话
- Resource Vault 仍归属于 Workspace

### 8.3 为什么必须做目标级会话

否则会出现：

1. 路线图修改对话和章节讲解混在一起  
2. 用户返回章节后，聊天上下文严重污染  
3. 测验、Artifact、章节解释都挤在同一会话里，后期必然失控

---

## 九、开源方案复用清单

### 9.1 必须直接复用

| 能力 | 方案 |
|------|------|
| 双栏与面板布局 | `react-resizable-panels` |
| 画布动效切换 | `motion` / `framer-motion` |
| 路线图图形化 | `reactflow` + `dagre` |
| 流式 Markdown | 现有 `rich-streamdown.tsx` |
| Artifacts 拉取 | 现有 `deerflow-artifact-detail.tsx` / standalone api |
| Chat UI | 现有 `deerflow-chat-test` 组件 |

### 9.2 可以按需新增，但不是首版必须

| 能力 | 方案 |
|------|------|
| PDF 预览 | `react-pdf` 或 `@react-pdf-viewer/core` |
| 更强的白板式导图编辑 | `tldraw` |
| 文件打包下载 | `jszip` |

### 9.3 明确不建议自研

- 自研图布局引擎  
- 自研 Markdown 流式渲染  
- 自研 PDF Viewer  
- 自研白板系统  
- 自研会话虚拟列表基础设施

---

## 十、建议目录结构（重写版）

```text
frontend-next/components/fast-learning-workspace/
├── workspace-shell.tsx
├── workspace-store.ts
├── workspace-layout.tsx
├── hub/
│   ├── hub-view.tsx
│   ├── prompt-hero.tsx
│   └── resume-workspace-list.tsx
├── copilot/
│   ├── copilot-panel.tsx
│   ├── copilot-session-switcher.tsx
│   └── contextual-compose.tsx
├── canvas/
│   ├── canvas-host.tsx
│   ├── roadmap-outline-canvas.tsx
│   ├── roadmap-graph-canvas.tsx
│   ├── chapter-canvas.tsx
│   └── artifact-preview-canvas.tsx
├── vault/
│   ├── resource-vault-drawer.tsx
│   └── chapter-material-collector.tsx
├── quiz/
│   └── quiz-inline-card.tsx
└── lib/
    ├── roadmap-graph-adapter.ts
    ├── workspace-session-adapter.ts
    ├── workspace-artifact-adapter.ts
    └── generative-ui-registry.tsx
```

---

## 十一、分阶段实施计划

### M1：Workspace 壳与 Hub

**目标**：先把页面骨架改成 demo 的结构。

#### 工作内容

- 新建 `WorkspaceView` 状态机：`hub | roadmap | learning | preview`
- 新建 `workspace-store.ts`
- 搭建三栏壳：
  - 图标栏
  - 固定宽度 Copilot 左栏
  - 右脑主画布
- 实现 `HubView`
- 历史卡片先接：
  - `roadmapsApi.getMyRoadmaps()` 或
  - 现有 DeerFlow thread 列表 + 本地聚合

#### 验收

- 可从 Hub 新建与恢复
- 页面不再是「聊天居中」，而是「Copilot + 画布」双脑结构

### M2：路线图工作区接真实 `RoadmapFramework`

**目标**：用真实路线图替换 demo 的 `RoadmapNode[]`

#### 工作内容

- 直接接 `useRoadmap(roadmapId)`
- 右脑画布提供：
  - `roadmap_outline`
  - `roadmap_graph`
- 编写 `roadmap-graph-adapter.ts`
- Concept 点击后切换 `learning`

#### 验收

- 路线图 Outline 可读
- Graph 视图可点击 Concept 节点
- 不再依赖 mock 路线图结构

### M3：章节学习工作区接真实教程 / 资源 / Quiz

**目标**：让 Learning 页完全基于真实内容接口

#### 工作内容

- `chapter-canvas.tsx` 接 `contentApi.getTutorial`
- `chapter-material-collector.tsx` 接：
  - `contentApi.getResources`
  - 当前章节 Artifact 聚合
- Quiz 卡接 `contentApi.getQuiz`
- 提交答题结果接学习 API

#### 验收

- 点击 Concept 可加载真实教程
- 章节内可看到真实资源 / 测验
- Quiz 不再是 demo mock

### M4：Artifact 预览与 Resource Vault

**目标**：把 demo 的 Artifact 体系接入当前 DeerFlow 产物

#### 工作内容

- 重构当前 `deerflow-chat-box.tsx` 的 Artifacts 逻辑
- 抽出全局 `Resource Vault`
- 聊天里的 Artifact 卡片统一跳转 `preview`
- 预览页支持：
  - HTML
  - Markdown
  - PDF（如已接入）

#### 验收

- Artifact 既能在聊天里出现，也能在资源库里检索
- 主画布预览稳定可返回

### M5：目标级会话、划线答疑、体验闭环

**目标**：把 demo 最关键的「目标级会话」和沉浸体验补齐

#### 工作内容

- `roadmap` / `concept_id` 级会话切换
- 章节划线答疑
- 面包屑与学习进度联动
- 小屏适配：画布 / Copilot 切换

#### 验收

- 路线图讨论与章节讨论分离
- 用户动线完整闭环

---

## 十二、风险与待确认项

| 项 | 说明 |
|----|------|
| Workspace 主键来源 | 用 `roadmap_id` 还是 DeerFlow thread ID 作为一级主键，需要统一 |
| 目标级会话持久化 | 前端本地切分还是后端真正多会话支持，需要决定 |
| Artifact 元数据标准 | 当前仅 path 集合不足以支撑 Vault，需要规范 title/type/source_concept |
| PPT / Mindmap 预览格式 | 是 DeerFlow 输出 HTML、Markdown 还是二进制文件，需要与后端统一 |

---

## 十三、最终验收标准

- [ ] Hub 页面完整呈现「新建 + 恢复」双入口  
- [ ] 路线图工作区接真实 `RoadmapFramework`  
- [ ] 章节工作区接真实教程 / 资源 / Quiz  
- [ ] Copilot 会话至少按 `roadmap` / `concept_id` 两级上下文分离  
- [ ] Resource Vault 与主画布预览可用  
- [ ] 不再以 mock 路线图结构驱动主流程  
- [ ] 当前 DeerFlow 流式消息和 Artifact 能力未回归

---

## 十四、参考文件

### demo 项目

- `best-practice/fastlearning-ai/src/App.tsx`
- `best-practice/fastlearning-ai/src/components/HubView.tsx`
- `best-practice/fastlearning-ai/src/components/Copilot.tsx`
- `best-practice/fastlearning-ai/src/components/RoadmapView.tsx`
- `best-practice/fastlearning-ai/src/components/ContentView.tsx`
- `best-practice/fastlearning-ai/src/components/ArtifactPreview.tsx`

### 当前项目

- `components/deerflow-chat-test/deerflow-chat-test-page.tsx`
- `components/deerflow-chat-test/deerflow-chat-box.tsx`
- `components/deerflow-chat-test/deerflow-chat-state.ts`
- `components/markdown/rich-streamdown.tsx`
- `components/roadmap/roadmap-view.tsx`
- `lib/hooks/api/use-roadmap.ts`
- `lib/api/endpoints/roadmaps.ts`
- `lib/api/endpoints/content.ts`
- `types/generated/models.ts`

---

*文档结束。*
