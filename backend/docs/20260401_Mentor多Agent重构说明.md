# Mentor 多 Agent 重构说明

## 背景

原有 Mentor 链路存在以下问题：

- `MentorAgent` 体量过大，混合了 Prompt、工具策略、流式协议、工具执行、事件拼装等多层职责。
- 前端通过 `assistMode -> agentType` 的派生关系驱动聊天，语义不清晰。
- 后端存在动态路由、轻量模式解析和主动引导等旧逻辑，维护成本高。
- 流式输出、长期记忆和前端 UI 协议之间的边界不够明确。

本次重构的目标是：

- 改为前端显式选择 Agent，不再做后端动态路由。
- 引入更清晰的 Mentor 运行时分层，逐步向 deer-flow 的设计思想靠拢。
- 保持路线图生成主架构不变，仅重构聊天伴学链路。

## 本次方案

### 前端交互模型

聊天页改为 3 个固定 Tab：

- `答疑`：对应 `qa` Agent
- `导学`：对应 `guide` Agent
- `测验`：对应 `quiz` Agent

其中：

- 当前仅完整实现 `qa`
- `guide`、`quiz` 先提供独立入口和占位响应
- `qa` 额外支持风格切换：`casual` / `serious`

### 后端分发模型

后端不再根据用户输入意图自动决定走哪个 Agent。

新的请求模型由前端显式传入：

- `agent_kind`
- `qa_style`

服务层只做静态分发：

- `qa` -> `QaAgent`
- `guide` -> `GuideAgent`
- `quiz` -> `QuizAgent`

## 主要改动

### 一、后端运行时拆分

新增目录：

- `backend/app/services/learning/mentor/`

新增模块：

- `event_types.py`
  - 定义新的中性事件模型
  - 定义 `MentorAgentKind`、`MentorQaStyle`
- `prompt_builder.py`
  - 负责答疑 Agent 的 Prompt 渲染
- `tool_policy.py`
  - 负责首轮工具策略和参数补全
- `tool_executor.py`
  - 将现有 `ToolRegistry` 适配为 LangChain 可用工具
- `graph_runner.py`
  - 使用 LangChain `create_agent` 驱动答疑 Agent loop
- `runtime_factory.py`
  - 负责创建聊天运行时
- `agent_registry.py`
  - 管理固定 Agent 类型注册表

### 二、后端 Agent 拆分

新增：

- `backend/app/agents/qa_agent.py`
- `backend/app/agents/guide_agent.py`
- `backend/app/agents/quiz_agent.py`

说明：

- `QaAgent` 为当前主实现
- `GuideAgent` / `QuizAgent` 目前是占位 Agent

已删除：

- `backend/app/agents/mentor_agent.py`

### 三、工厂层调整

更新文件：

- `backend/app/agents/factory.py`

变更内容：

- 删除旧的 `create_mentor_agent()`
- 新增：
  - `create_qa_agent()`
  - `create_guide_agent()`
  - `create_quiz_agent()`

### 四、服务层调整

更新文件：

- `backend/app/services/learning/mentor_service.py`

关键变化：

- 不再做动态 Agent 路由
- 不再依赖 `assistMode -> resolvedAgentType` 的旧链路
- 引入 `MentorChatAgentContext`
- 新增轻量情绪识别 `_analyze_user_emotion()`
- 记忆任务 payload 中新增：
  - `agent_kind`
  - `qa_style`
  - `emotion_label`
  - `emotion_summary`
- SSE 事件主形态继续兼容：
  - `meta`
  - `thinking`
  - `delta`
  - `tool_start`
  - `tool_result`

已移除的旧逻辑：

- `MentorAssistStrategy`
- `MentorAssistModeDecision`
- 动态 assist mode 解析
- resolver agent 驱动的模式路由
- transition hint / suggested actions 生成逻辑

### 五、Prompt 调整

新增文件：

- `backend/prompts/qa_agent.j2`

特点：

- 只面向答疑场景
- 支持 `qa_style`
- 支持情绪标签与情绪摘要注入
- 明确禁止在回复中暴露内部 Agent 切换和内部机制

### 六、前端协议调整

主要更新目录：

- `frontend-next/components/mentor/`

关键变化：

- `types.ts`
  - 新主模型：`MentorAgentKind`
  - 新主模型：`MentorQaStyle`
  - 移除旧的 `assistMode / resolvedAssistMode` 主导地位
- `mentor-api.ts`
  - 请求改为发送 `agent_kind` 与 `qa_style`
- `mentor-adapter.ts`
  - 元数据改为读取 `agentKind / qaStyle / emotionLabel / emotionSummary`
- `use-mentor-runtime.ts`
  - 运行时基于 `agentKind + qaStyle`
- `use-mentor-threads.ts`
  - 本地线程状态改为围绕 `agentKind + qaStyle`
- `mentor-toolbar.tsx`
  - 增加 3 个 Tab 和 QA 风格切换
- `mentor-composer.tsx`
  - 接入新的工具栏状态
- `mentor-sidebar.tsx`
  - 运行时主状态切到 `agentKind + qaStyle`

## 数据兼容说明

本次重构没有新增数据库迁移。

当前数据库中以下字段继续沿用旧列名，但语义已经切换：

- `chat_sessions.agent_type`
- `chat_messages.agent_type`

当前实际存储的是新的 `agent_kind` 语义：

- `qa`
- `guide`
- `quiz`

这意味着：

- 代码层已经切到新模型
- 数据库层仍保留旧字段名
- 后续如果需要彻底整洁化，可以单独补一次字段重命名迁移

## 测试情况

本次新增或更新了与新架构对应的测试：

- `backend/tests/agents/test_qa_agent.py`
- `backend/tests/unit/test_mentor_service_v2.py`
- `frontend-next/__tests__/unit/components/mentor/mentor-chat.test.ts`
- `frontend-next/__tests__/unit/components/mentor/mentor-adapter.test.ts`

已验证：

- 后端新测试通过
- 前端 Mentor 相关单测通过
- 本轮修改文件无新的 linter 报错

## 当前状态

已完成：

- 前端显式选 Agent
- 后端静态分发 Agent
- `qa` 风格切换
- `qa` 情绪识别
- 记忆任务携带新字段
- `guide` / `quiz` 占位入口
- `MentorService` 清理旧动态路由逻辑

未完成：

- `guide` Agent 实际导学能力
- `quiz` Agent 实际测验能力
- 数据库字段名与业务语义完全对齐
- 更完整的 LangGraph 状态图可视化与中间事件抽象

## 后续建议

建议按以下顺序继续演进：

1. 先补 `guide` 和 `quiz` 的真实业务能力，不改当前静态分发模型。
2. 再补数据库迁移，把 `agent_type` 字段语义彻底切换为 `agent_kind`。
3. 最后继续细化 `QaAgent` 的 LangChain / LangGraph 事件结构，使工具事件与最终消息快照进一步解耦。
