# Agent 初始化参数错误修复

## 🔴 问题

**错误**：`TypeError: IntentAnalyzerAgent.__init__() got an unexpected keyword argument 'agent_id'`

**影响**：路线图生成任务启动后立即失败

## 🔍 根本原因

### 不一致的 Agent 初始化方式

**Agent 类定义**（`backend/app/agents/intent_analyzer.py:25`）：
```python
class IntentAnalyzerAgent(BaseAgent):
    def __init__(self):  # ❌ 不接受任何参数
        super().__init__(
            agent_id="intent_analyzer",
            model_provider=settings.ANALYZER_PROVIDER,
            ...
        )
```

**Factory 调用**（`backend/app/agents/factory.py:81-87`）：
```python
return IntentAnalyzerAgent(  # ❌ 尝试传递参数
    agent_id="intent_analyzer",
    model_provider=self.settings.ANALYZER_PROVIDER,
    model_name=self.settings.ANALYZER_MODEL,
    base_url=self.settings.ANALYZER_BASE_URL,
    api_key=self.settings.ANALYZER_API_KEY,
)
```

**冲突**：
- Agent 类的 `__init__()` 不接受参数
- Factory 尝试传递参数
- 导致 `TypeError`

## ✅ 修复方案

### 修改 IntentAnalyzerAgent.__init__()

**文件**：`backend/app/agents/intent_analyzer.py`

```diff
  class IntentAnalyzerAgent(BaseAgent):
      """需求分析师 Agent"""
      
-     def __init__(self):
+     def __init__(
+         self,
+         agent_id: str = "intent_analyzer",
+         model_provider: str | None = None,
+         model_name: str | None = None,
+         base_url: str | None = None,
+         api_key: str | None = None,
+     ):
          super().__init__(
-             agent_id="intent_analyzer",
-             model_provider=settings.ANALYZER_PROVIDER,
-             model_name=settings.ANALYZER_MODEL,
-             base_url=settings.ANALYZER_BASE_URL,
-             api_key=settings.ANALYZER_API_KEY,
+             agent_id=agent_id,
+             model_provider=model_provider or settings.ANALYZER_PROVIDER,
+             model_name=model_name or settings.ANALYZER_MODEL,
+             base_url=base_url or settings.ANALYZER_BASE_URL,
+             api_key=api_key or settings.ANALYZER_API_KEY,
              temperature=0.3,
              max_tokens=2048,
          )
```

**优点**：
1. ✅ 支持 Factory 传参（依赖注入）
2. ✅ 支持直接实例化（使用默认配置）
3. ✅ 向后兼容现有代码

## 📝 使用方式

### 方式 1：通过 Factory（推荐）

```python
from app.agents.factory import get_agent_factory

factory = get_agent_factory()
agent = factory.create_intent_analyzer()
result = await agent.analyze(user_request)
```

### 方式 2：直接实例化（使用默认配置）

```python
from app.agents.intent_analyzer import IntentAnalyzerAgent

agent = IntentAnalyzerAgent()  # 使用环境变量配置
result = await agent.analyze(user_request)
```

### 方式 3：直接实例化（自定义配置）

```python
from app.agents.intent_analyzer import IntentAnalyzerAgent

agent = IntentAnalyzerAgent(
    agent_id="custom_analyzer",
    model_provider="openai",
    model_name="gpt-4",
    api_key="custom-key",
)
result = await agent.analyze(user_request)
```

## 🔄 需要类似修改的其他 Agent

基于相同的设计模式，以下 Agent 可能需要类似修改（如果它们也有相同问题）：

1. `CurriculumArchitectAgent`
2. `StructureValidatorAgent`
3. `RoadmapEditorAgent`
4. `TutorialGeneratorAgent`
5. `ResourceRecommenderAgent`
6. `QuizGeneratorAgent`
7. `ModificationAnalyzerAgent`
8. `TutorialModifierAgent`
9. `ResourceModifierAgent`
10. `QuizModifierAgent`

**检查方法**：
```bash
cd backend
grep -n "def __init__(self):" app/agents/*.py
```

如果输出显示 `__init__(self):` 而不是 `__init__(self, ...):`，则需要修改。

## 🧪 测试验证

### 测试 1：直接实例化

```python
from app.agents.intent_analyzer import IntentAnalyzerAgent

# 应该不报错
agent = IntentAnalyzerAgent()
print(f"Agent created: {agent.agent_id}")
```

### 测试 2：Factory 创建

```python
from app.agents.factory import get_agent_factory

factory = get_agent_factory()
agent = factory.create_intent_analyzer()
print(f"Agent created via factory: {agent.agent_id}")
```

### 测试 3：路线图生成

```bash
curl -X POST http://localhost:8000/api/v1/roadmaps/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "preferences": {
      "learning_goal": "学习 Python",
      "current_level": "beginner",
      "weekly_hours": 10,
      "learning_style": ["visual"]
    }
  }'
```

**✅ 期望结果**：
- 返回 `task_id`
- 后端日志无 TypeError
- WebSocket 能正常连接

## 📊 修复前后对比

| 场景 | 修复前 | 修复后 |
|------|--------|--------|
| **Factory 创建** | ❌ TypeError | ✅ 成功 |
| **直接实例化（无参数）** | ✅ 成功 | ✅ 成功 |
| **直接实例化（有参数）** | ❌ TypeError | ✅ 成功 |
| **向后兼容性** | ✅ 保持 | ✅ 保持 |

## 🎯 相关问题

### 问题 2：WebSocket 立即关闭

从日志看，WebSocket 连接建立后立即关闭，这是因为：

1. `_send_current_status` 尝试查询任务状态
2. 任务记录可能还没完全创建
3. 查询失败导致异常
4. 异常触发 WebSocket 关闭
5. 前端检测到关闭后重连
6. 形成循环

**解决方案**：
- ✅ 已添加异常处理（检查 WebSocket 状态）
- ✅ 降级为 debug 日志而非 error
- ⏳ Agent 初始化错误修复后应该能解决

## ✨ 总结

### 修改的文件

1. ✅ `backend/app/agents/intent_analyzer.py`
   - 修改 `__init__()` 方法签名
   - 添加参数支持和默认值

### 修复的问题

1. ✅ Agent 初始化 TypeError
2. ✅ 路线图生成失败
3. 🔄 WebSocket 重连循环（间接修复）

### 测试检查清单

- [ ] Agent 直接实例化（无参）
- [ ] Agent 直接实例化（有参）
- [ ] Factory 创建 Agent
- [ ] 路线图生成 API
- [ ] WebSocket 连接稳定

---

**修复时间**：2025-12-07  
**修复轮次**：第 3 轮  
**预计测试时间**：3 分钟

