# Tasks: FastLearning Workspace（学习空间）前端重构

**Input**: 基于 `frontend-next/docs/20260406_FastLearning工作区前端实施计划.md` 反推生成  
**Prerequisites**: 当前仓库未处于 Speckit 特性分支，且不存在对应 `specs/.../plan.md` / `spec.md`；以下任务按实施计划中的 `M1` 到 `M5` 作为用户故事等价拆分  
**Tests**: 本轮未强制采用 TDD，测试任务不单列为前置阶段；每个用户故事仍提供独立验收标准  
**Organization**: 任务按阶段与用户故事组织，确保可独立实现与验收

## Format: `[ID] [P?] [Story] Description`

- **[P]**：可并行执行（不同文件、无未完成前置依赖）
- **[Story]**：用户故事标签，对应 `US1` 到 `US5`
- **Description**：包含明确动作与精确文件路径

## Phase 1: Setup（项目落位与脚手架）

**Purpose**: 为 Workspace 重构建立新的组件目录、入口与基础导出结构

- [ ] T001 创建 `frontend-next/components/fast-learning-workspace/` 及其 `hub/`、`copilot/`、`canvas/`、`vault/`、`quiz/`、`lib/` 子目录，并补齐首批占位文件
- [ ] T002 创建 `frontend-next/components/fast-learning-workspace/workspace-shell.tsx` 作为 Workspace 顶层入口组件
- [ ] T003 [P] 创建 `frontend-next/components/fast-learning-workspace/workspace-layout.tsx` 作为三栏壳布局骨架
- [ ] T004 [P] 创建 `frontend-next/components/fast-learning-workspace/workspace-store.ts` 定义 `hub | roadmap | learning | preview` 视图状态与核心 actions
- [ ] T005 更新 `frontend-next/app/(immersive)/deer-flow-chat-test/page.tsx`，将沉浸式路由入口切换到新的 Workspace 壳组件

---

## Phase 2: Foundational（阻塞性基础能力）

**Purpose**: 完成所有用户故事共享的数据适配、画布宿主、Copilot 包装与 Artifact 注册层

**⚠️ CRITICAL**: 本阶段完成前，不建议开始任一用户故事实现

- [ ] T006 创建 `frontend-next/components/fast-learning-workspace/canvas/canvas-host.tsx`，统一承接 `roadmap_outline`、`roadmap_graph`、`chapter_reader`、`artifact_preview` 四类画布模式
- [ ] T007 [P] 创建 `frontend-next/components/fast-learning-workspace/copilot/copilot-panel.tsx`，将现有 `components/deerflow-chat-test/*` 能力封装成 Workspace 左栏
- [ ] T008 [P] 创建 `frontend-next/components/fast-learning-workspace/lib/workspace-session-adapter.ts`，定义 `roadmap` 与 `concept:{concept_id}` 会话目标映射协议
- [ ] T009 [P] 创建 `frontend-next/components/fast-learning-workspace/lib/workspace-artifact-adapter.ts`，统一 DeerFlow Artifact、内容资源、Vault 条目结构
- [ ] T010 [P] 创建 `frontend-next/components/fast-learning-workspace/lib/generative-ui-registry.tsx`，统一注册 Quiz 卡片、Artifact 卡片、预览入口等生成式 UI
- [ ] T011 在 `frontend-next/components/fast-learning-workspace/workspace-layout.tsx` 接入图标栏、固定 Copilot 左栏与右侧主画布容器
- [ ] T012 在 `frontend-next/components/fast-learning-workspace/workspace-shell.tsx` 串联 `workspace-store.ts`、`workspace-layout.tsx` 与 `canvas-host.tsx` 的基础状态流转

**Checkpoint**: Foundation ready，后续用户故事可按优先级增量推进

---

## Phase 3: User Story 1 - Hub 与 Workspace 壳（Priority: P1）🎯 MVP

**Goal**: 用户可以从 Hub 页面创建新学习空间或恢复已有路线图，并进入新的双脑工作区壳

**Independent Test**: 打开 `app/(immersive)/deer-flow-chat-test/page.tsx` 后，默认进入 Hub；能看到中心 Hero 与恢复学习卡片；点击开始或恢复后切到 `roadmap` 视图，页面不再是居中聊天页

### Implementation for User Story 1

- [ ] T013 [P] [US1] 实现 `frontend-next/components/fast-learning-workspace/hub/prompt-hero.tsx`，提供 Hub 中央输入框、推荐标签与 Start 动作
- [ ] T014 [P] [US1] 实现 `frontend-next/components/fast-learning-workspace/hub/resume-workspace-list.tsx`，承接恢复学习卡片列表渲染
- [ ] T015 [US1] 实现 `frontend-next/components/fast-learning-workspace/hub/hub-view.tsx`，组合 `prompt-hero.tsx` 与 `resume-workspace-list.tsx`
- [ ] T016 [US1] 在 `frontend-next/components/fast-learning-workspace/hub/hub-view.tsx` 接入 `frontend-next/lib/api/endpoints/roadmaps.ts` 的 `roadmapsApi.getMyRoadmaps()`
- [ ] T017 [US1] 在 `frontend-next/components/fast-learning-workspace/workspace-store.ts` 增加 Hub 新建、恢复、进入 `roadmap` 视图的导航动作
- [ ] T018 [US1] 在 `frontend-next/components/fast-learning-workspace/workspace-shell.tsx` 中接入 `hub-view.tsx`，并完成 Hub 与路由入口的首屏切换

**Checkpoint**: User Story 1 完成后，Workspace 已具备可演示的入口、恢复与壳结构

---

## Phase 4: User Story 2 - 路线图工作区接真实 `RoadmapFramework`（Priority: P1）

**Goal**: 路线图工作区改为基于真实 `RoadmapFramework` 渲染 Outline / Graph 双视图，并支持点击 Concept 进入学习态

**Independent Test**: 从 Hub 进入某个 roadmap 后，右侧可以看到真实路线图 Outline 与 Graph；两种视图可切换；点击 Concept 节点会把当前视图切到 `learning`

### Implementation for User Story 2

- [ ] T019 [P] [US2] 实现 `frontend-next/components/fast-learning-workspace/canvas/roadmap-outline-canvas.tsx`，复用 `frontend-next/components/roadmap/roadmap-view.tsx` 渲染真实路线图层级
- [ ] T020 [P] [US2] 实现 `frontend-next/components/fast-learning-workspace/lib/roadmap-graph-adapter.ts`，将 `RoadmapFramework` 转换为 React Flow 所需 `nodes` / `edges`
- [ ] T021 [P] [US2] 实现 `frontend-next/components/fast-learning-workspace/canvas/roadmap-graph-canvas.tsx`，使用 `reactflow` + `dagre` 渲染知识图
- [ ] T022 [US2] 在 `frontend-next/components/fast-learning-workspace/canvas/canvas-host.tsx` 中接入 `frontend-next/lib/hooks/api/use-roadmap.ts` 与双视图切换逻辑
- [ ] T023 [US2] 在 `frontend-next/components/fast-learning-workspace/workspace-store.ts` 中增加 `roadmap_outline`、`roadmap_graph`、当前 `concept_id` 与当前 `roadmap_id` 的状态管理
- [ ] T024 [US2] 在 `frontend-next/components/fast-learning-workspace/workspace-shell.tsx` 中打通 Concept 点击、选中节点与跳转 `learning` 视图的动作

**Checkpoint**: User Story 2 完成后，路线图主画布不再依赖 mock 结构

---

## Phase 5: User Story 3 - 章节学习工作区接真实教程 / 资源 / Quiz（Priority: P1）

**Goal**: 章节学习态完全基于真实内容接口运行，支持阅读教程、查看资源、加载测验并提交结果

**Independent Test**: 在路线图画布点击任一 Concept 后，右侧能加载真实教程正文；资源列表与 Quiz 卡片可见；提交 Quiz 后有结果反馈且进度状态更新

### Implementation for User Story 3

- [ ] T025 [P] [US3] 实现 `frontend-next/components/fast-learning-workspace/canvas/chapter-canvas.tsx`，接入 `frontend-next/lib/api/endpoints/content.ts` 的 `contentApi.getTutorial()`
- [ ] T026 [P] [US3] 实现 `frontend-next/components/fast-learning-workspace/vault/chapter-material-collector.tsx`，接入 `contentApi.getResources()` 并汇聚当前章节 Artifact
- [ ] T027 [P] [US3] 实现 `frontend-next/components/fast-learning-workspace/quiz/quiz-inline-card.tsx`，接入 `contentApi.getQuiz()` 与 `frontend-next/lib/api/endpoints/learning.ts` 的 `learningApi.submitQuizAttempt()`
- [ ] T028 [US3] 在 `frontend-next/components/fast-learning-workspace/canvas/chapter-canvas.tsx` 中补齐章节 Header、返回路线图、资料夹入口与多模态按钮区
- [ ] T029 [US3] 在 `frontend-next/components/fast-learning-workspace/workspace-store.ts` 中增加章节级加载状态、Quiz 提交结果与当前章节资源缓存
- [ ] T030 [US3] 在 `frontend-next/components/fast-learning-workspace/canvas/roadmap-outline-canvas.tsx` 与 `workspace-store.ts` 中接入基于真实内容状态的学习进度映射

**Checkpoint**: User Story 3 完成后，学习态具备完整的真实内容阅读闭环

---

## Phase 6: User Story 4 - Artifact 预览与 Resource Vault（Priority: P2）

**Goal**: Artifact 在聊天中、资源库中、主画布预览中三处打通，并形成稳定的预览返回链路

**Independent Test**: 在聊天或资料夹中点击任一 Artifact / 资源后，主画布切到 `preview`；支持 Markdown / HTML / PDF 三类基础预览；关闭预览后能回到原来的 `learning` 或 `roadmap`

### Implementation for User Story 4

- [ ] T031 [P] [US4] 实现 `frontend-next/components/fast-learning-workspace/canvas/artifact-preview-canvas.tsx`，支持 Markdown、HTML、PDF 三类预览容器
- [ ] T032 [P] [US4] 实现 `frontend-next/components/fast-learning-workspace/vault/resource-vault-drawer.tsx`，提供全 Workspace 资源汇总、章节筛选与条目点击
- [ ] T033 [US4] 在 `frontend-next/components/fast-learning-workspace/lib/workspace-artifact-adapter.ts` 中补齐 Artifact 标题、类型、来源章节与预览地址的标准化映射
- [ ] T034 [US4] 在 `frontend-next/components/deerflow-chat-test/deerflow-artifact-trigger.tsx` 与 `frontend-next/components/fast-learning-workspace/copilot/copilot-panel.tsx` 中接入统一的预览打开事件
- [ ] T035 [US4] 在 `frontend-next/components/fast-learning-workspace/workspace-store.ts` 中增加 `preview` 返回来源、Vault 开关与当前预览条目状态
- [ ] T036 [US4] 在 `frontend-next/components/fast-learning-workspace/workspace-shell.tsx` 与 `canvas/canvas-host.tsx` 中打通 Vault、聊天卡片、主画布预览三者联动

**Checkpoint**: User Story 4 完成后，Artifact 体系已从聊天附件升级为 Workspace 级能力

---

## Phase 7: User Story 5 - 目标级会话与沉浸式体验闭环（Priority: P2）

**Goal**: 按 `roadmap` / `concept:{concept_id}` 切分会话语境，补齐面包屑、学习进度、小屏切换与划线答疑体验

**Independent Test**: 从路线图讨论切进章节讨论后，左栏会话标题与历史切换到章节语境；返回路线图后恢复路线图语境；小屏可在画布与 Copilot 之间切换；章节文本可发起带上下文的提问

### Implementation for User Story 5

- [ ] T037 [P] [US5] 实现 `frontend-next/components/fast-learning-workspace/copilot/copilot-session-switcher.tsx`，展示 `roadmap` 与 `concept:{concept_id}` 的会话切换器
- [ ] T038 [P] [US5] 实现 `frontend-next/components/fast-learning-workspace/copilot/contextual-compose.tsx`，在发送消息时注入当前目标、章节上下文与引用片段
- [ ] T039 [US5] 在 `frontend-next/components/fast-learning-workspace/lib/workspace-session-adapter.ts` 与 `frontend-next/components/deerflow-chat-test/deerflow-chat-state.ts` 中实现目标级消息分组与过滤
- [ ] T040 [US5] 在 `frontend-next/components/fast-learning-workspace/copilot/copilot-panel.tsx` 中接入会话切换器、上下文标题与目标级历史展示
- [ ] T041 [US5] 在 `frontend-next/components/fast-learning-workspace/workspace-layout.tsx` 与 `workspace-shell.tsx` 中增加面包屑、学习进度展示与小屏画布 / Copilot 切换
- [ ] T042 [US5] 在 `frontend-next/components/fast-learning-workspace/canvas/chapter-canvas.tsx` 与 `copilot/contextual-compose.tsx` 中实现章节划线答疑入口

**Checkpoint**: User Story 5 完成后，Workspace 具备 demo 中最关键的目标级会话与沉浸式体验

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: 收尾跨阶段问题，降低回归风险并沉淀交付说明

- [ ] T043 [P] 为 `frontend-next/components/fast-learning-workspace/` 下所有新组件补齐 loading / empty / error UI 与可访问性属性
- [ ] T044 [P] 清理 `frontend-next/components/deerflow-chat-test/` 中被 Workspace 替代的重复入口和无效分支，确保旧能力不残留双份状态源
- [ ] T045 梳理 `frontend-next/components/fast-learning-workspace/lib/workspace-artifact-adapter.ts` 与后端协议差异，并回写到 `frontend-next/docs/20260406_FastLearning工作区前端实施计划.md`
- [ ] T046 在 `frontend-next/docs/20260406_FastLearning工作区前端阶段任务.md` 末尾补充人工冒烟记录与已完成任务勾选说明

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup（Phase 1）**：可立即开始
- **Foundational（Phase 2）**：依赖 Setup 完成，阻塞全部用户故事
- **US1 / US2 / US3**：均依赖 Foundational 完成；建议按 `US1 -> US2 -> US3` 顺序推进以快速形成 MVP
- **US4 / US5**：依赖 `US2` 与 `US3` 的主流程稳定后再接入
- **Polish（Phase 8）**：依赖目标范围内的用户故事完成

### User Story Dependencies

- **US1**：无其他用户故事依赖，是最小可演示入口
- **US2**：依赖 US1 的 Workspace 壳与 store，但可独立验证路线图工作区
- **US3**：依赖 US2 的 Concept 选中与路由状态，但可独立验证学习态
- **US4**：依赖 US3 的章节资源与现有 DeerFlow Artifact 数据
- **US5**：依赖 US2 / US3 的上下文切换能力与主流程闭环

### Within Each User Story

- 先完成该阶段的状态与适配层，再落 UI 组件
- 先完成画布 / 数据加载，再接入跨组件导航动作
- 先保证单阶段可独立验收，再继续下一个阶段

### Parallel Opportunities

- Setup 中 `T003`、`T004` 可并行
- Foundational 中 `T007`、`T008`、`T009`、`T010` 可并行
- US1 中 `T013`、`T014` 可并行
- US2 中 `T019`、`T020`、`T021` 可并行
- US3 中 `T025`、`T026`、`T027` 可并行
- US4 中 `T031`、`T032` 可并行
- US5 中 `T037`、`T038` 可并行

---

## Parallel Example: User Story 3

```bash
Task: "实现 frontend-next/components/fast-learning-workspace/canvas/chapter-canvas.tsx，接入 contentApi.getTutorial()"
Task: "实现 frontend-next/components/fast-learning-workspace/vault/chapter-material-collector.tsx，接入 contentApi.getResources()"
Task: "实现 frontend-next/components/fast-learning-workspace/quiz/quiz-inline-card.tsx，接入 contentApi.getQuiz() 与 learningApi.submitQuizAttempt()"
```

---

## Implementation Strategy

### MVP First（只做 P1）

1. 完成 Phase 1 Setup
2. 完成 Phase 2 Foundational
3. 完成 Phase 3 US1
4. 完成 Phase 4 US2
5. 完成 Phase 5 US3
6. 以 `Hub -> Roadmap -> Learning` 主链路做一次人工验收

### Incremental Delivery

1. 先交付 `US1`，验证新 Workspace 壳与 Hub 入口
2. 再交付 `US2`，让真实路线图替换 mock 主画布
3. 再交付 `US3`，形成真实学习内容闭环
4. 最后补齐 `US4` 与 `US5`，增强 Artifact 体系与会话体验

### Suggested MVP Scope

- 建议 MVP 以 `US1 + US2 + US3` 为最小可用闭环
- 如果必须进一步压缩范围，则只保留 `US1` 作为第一轮演示入口

---

## Story Summary

- **US1**：Hub 与 Workspace 壳，任务数 `6`
- **US2**：真实路线图工作区，任务数 `6`
- **US3**：真实教程 / 资源 / Quiz，任务数 `6`
- **US4**：Artifact 预览与 Resource Vault，任务数 `6`
- **US5**：目标级会话与体验闭环，任务数 `6`

## Notes

- 总任务数：`46`
- 标注 `[P]` 的任务均已控制为不同文件、可并行推进
- 所有任务均采用 `- [ ] Txxx ...` 清单格式
- 由于当前不在 Speckit 特性分支，本文件是对 `/speckit.tasks` 的等价人工产出
