# 技术栈能力分析 - 快速参考

## API端点

### 1. 评估答案（计算分数）

```http
POST /api/v1/tech-assessments/{technology}/{proficiency}/evaluate
```

**请求体**：
```json
{
  "answers": ["选项A", "选项B", "选项C", ...]  // 20个答案
}
```

**响应**：
```json
{
  "score": 31,                    // 得分
  "max_score": 39,                // 总分
  "percentage": 79.5,             // 正确率
  "correct_count": 15,            // 答对题数
  "total_questions": 20,          // 总题数
  "recommendation": "confirmed",  // confirmed/adjust/downgrade
  "message": "您的能力与当前级别匹配，继续保持！"
}
```

### 2. 能力分析（LLM深度分析）⭐ 新功能

```http
POST /api/v1/tech-assessments/{technology}/{proficiency}/analyze
```

**请求体**：
```json
{
  "user_id": "user123",
  "answers": ["选项A", "选项B", ...],  // 20个答案
  "save_to_profile": true             // 是否保存到用户画像
}
```

**响应**：
```json
{
  "technology": "python",
  "proficiency_level": "intermediate",
  "overall_assessment": "用户在Python中级水平测试中表现良好，基础知识非常扎实...",
  "strengths": [
    "Python基础语法和数据结构掌握扎实",
    "面向对象编程理解透彻"
  ],
  "weaknesses": [
    "装饰器的高级用法理解不够深入",
    "元类概念模糊"
  ],
  "knowledge_gaps": [
    {
      "topic": "Python元编程（装饰器、元类、描述符）",
      "description": "元编程是Python高级特性的核心，涉及动态修改类和函数行为...",
      "priority": "high",  // high/medium/low
      "recommendations": [
        "系统学习《Fluent Python》第7章",
        "实践：尝试实现一个简单的ORM框架"
      ]
    }
  ],
  "learning_suggestions": [
    "继续巩固中级知识，重点突破装饰器和元类等高级特性",
    "多阅读优秀的Python开源项目源码"
  ],
  "proficiency_verification": {
    "claimed_level": "intermediate",      // 声称的级别
    "verified_level": "intermediate",     // 验证的实际级别
    "confidence": "high",                 // high/medium/low
    "reasoning": "用户的测试表现完全符合中级水平标准：基础题全对..."
  },
  "score_breakdown": {
    "easy": {
      "correct": 7,
      "total": 7,
      "percentage": 100.0
    },
    "medium": {
      "correct": 6,
      "total": 7,
      "percentage": 85.7
    },
    "hard": {
      "correct": 2,
      "total": 6,
      "percentage": 33.3
    }
  }
}
```

## 前端集成步骤

### Step 1: 用户完成测试并提交

```typescript
// 调用评估API
const evaluateResult = await fetch(
  `/api/v1/tech-assessments/${technology}/${proficiency}/evaluate`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answers: userAnswers })
  }
).then(res => res.json());

// 显示评估结果
showEvaluationResult(evaluateResult);
```

### Step 2: 用户点击"能力分析"按钮

```typescript
// 调用能力分析API
const analysisResult = await fetch(
  `/api/v1/tech-assessments/${technology}/${proficiency}/analyze`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id: currentUserId,
      answers: userAnswers,
      save_to_profile: true  // 保存到用户画像
    })
  }
).then(res => res.json());

// 显示能力分析报告
showCapabilityAnalysisReport(analysisResult);
```

### Step 3: 展示能力分析报告

```typescript
interface CapabilityAnalysisReport {
  technology: string;
  proficiency_level: string;
  overall_assessment: string;
  strengths: string[];
  weaknesses: string[];
  knowledge_gaps: KnowledgeGap[];
  learning_suggestions: string[];
  proficiency_verification: ProficiencyVerification;
  score_breakdown: ScoreBreakdown;
}

interface KnowledgeGap {
  topic: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  recommendations: string[];
}

interface ProficiencyVerification {
  claimed_level: string;
  verified_level: string;
  confidence: 'high' | 'medium' | 'low';
  reasoning: string;
}

interface ScoreBreakdown {
  easy: ScoreBreakdownItem;
  medium: ScoreBreakdownItem;
  hard: ScoreBreakdownItem;
}

interface ScoreBreakdownItem {
  correct: number;
  total: number;
  percentage: number;
}
```

## UI设计建议

### 1. 整体评价区域
```
┌─────────────────────────────────────────┐
│ 📊 整体能力评价                          │
├─────────────────────────────────────────┤
│ 用户在Python中级水平测试中表现良好，     │
│ 基础知识非常扎实，所有简单题全部答对。   │
│ 中等难度题目掌握情况优秀...             │
└─────────────────────────────────────────┘
```

### 2. 优势与薄弱点
```
┌─────────────────────────────────────────┐
│ ✅ 优势领域                              │
├─────────────────────────────────────────┤
│ 🟢 Python基础语法和数据结构掌握扎实      │
│ 🟢 面向对象编程理解透彻                  │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ ⚠️ 薄弱环节                              │
├─────────────────────────────────────────┤
│ 🟡 装饰器的高级用法理解不够深入          │
│ 🟡 元类概念模糊                          │
└─────────────────────────────────────────┘
```

### 3. 知识缺口（可折叠卡片）
```
┌─────────────────────────────────────────┐
│ 🔴 Python元编程           [高优先级]     │
├─────────────────────────────────────────┤
│ 元编程是Python高级特性的核心，涉及动态   │
│ 修改类和函数行为。错题显示你对装饰器...  │
│                                          │
│ 💡 学习建议：                            │
│ • 系统学习《Fluent Python》第7章        │
│ • 实践：实现一个简单的ORM框架            │
└─────────────────────────────────────────┘
```

### 4. 能力级别验证
```
┌─────────────────────────────────────────┐
│ 🎯 能力级别验证                          │
├─────────────────────────────────────────┤
│ 声称级别: Intermediate                   │
│ 实际级别: ✅ Intermediate (高置信度)     │
│                                          │
│ 判定依据：                               │
│ 用户的测试表现完全符合中级水平标准：     │
│ 基础题全对（100%），中等题正确率85.7%... │
└─────────────────────────────────────────┘
```

### 5. 分数细分图表
```
┌─────────────────────────────────────────┐
│ 📈 各难度得分情况                        │
├─────────────────────────────────────────┤
│ 简单题: ████████████████████ 100%       │
│         (7/7)                            │
│                                          │
│ 中等题: ████████████████░░░░ 85.7%      │
│         (6/7)                            │
│                                          │
│ 困难题: ███████░░░░░░░░░░░░░ 33.3%      │
│         (2/6)                            │
└─────────────────────────────────────────┘
```

## 数据流向

```
用户答题
  ↓
[提交] 按钮
  ↓
POST /evaluate
  ↓
显示评估结果（分数、正确率、建议）
  ↓
[能力分析] 按钮
  ↓
POST /analyze
  ↓
LLM深度分析（10-20秒）
  ↓
保存到 user_profiles.tech_stack
  ↓
显示能力分析报告
  ↓
后续生成路线图时，IntentAnalyzer会自动利用这些分析结果
```

## 优先级标识

| 优先级 | 颜色 | 图标 | 说明 |
|--------|------|------|------|
| high | 🔴 红色 | ⚠️ | 基础性知识缺失，影响后续学习 |
| medium | 🟡 黄色 | ℹ️ | 进阶知识不足，影响深入理解 |
| low | 🟢 绿色 | 💡 | 边缘知识点，可后续补充 |

## 能力级别验证结果

| 验证结果 | 图标 | 说明 |
|---------|------|------|
| 验证通过 | ✅ | 实际级别 = 声称级别 |
| 高估 | ⚠️ | 实际级别 < 声称级别 |
| 低估 | 🎉 | 实际级别 > 声称级别 |

## 置信度标识

| 置信度 | 说明 |
|--------|------|
| high | 判定依据充分，结果可靠 |
| medium | 判定依据一般，建议再次测试 |
| low | 判定依据不足，强烈建议重测 |

## 错误处理

### 404 - 测验不存在
```json
{
  "detail": "Assessment not found for python-intermediate"
}
```

### 400 - 答案数量不匹配
```json
{
  "detail": "Expected 20 answers, got 18"
}
```

### 500 - 分析失败
```json
{
  "detail": "Capability analysis failed: LLM timeout"
}
```

## 性能考虑

- **评估API**：< 100ms（纯计算）
- **能力分析API**：10-20秒（LLM调用）
  - 建议显示加载动画
  - 可考虑添加进度提示

## 后续利用

能力分析结果保存到用户画像后，会在以下场景自动利用：

1. **生成新路线图时**
   - IntentAnalyzer会读取能力分析结果
   - 避免重复优势领域
   - 重点补强薄弱环节
   - 优先解决高优先级知识缺口

2. **推荐学习资源时**
   - 根据知识缺口推荐相关资源
   - 根据学习建议推荐课程

3. **伴学答疑时**
   - QAAgent可获取能力分析
   - 提供更针对性的讲解

## 示例代码

### React组件示例

```tsx
import React, { useState } from 'react';

interface CapabilityAnalysisProps {
  technology: string;
  proficiency: string;
  userAnswers: string[];
  userId: string;
}

export const CapabilityAnalysis: React.FC<CapabilityAnalysisProps> = ({
  technology,
  proficiency,
  userAnswers,
  userId
}) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/v1/tech-assessments/${technology}/${proficiency}/analyze`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user_id: userId,
            answers: userAnswers,
            save_to_profile: true
          })
        }
      );
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Analysis failed:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button onClick={handleAnalyze} disabled={loading}>
        {loading ? '分析中...' : '能力分析'}
      </button>
      
      {result && (
        <div className="analysis-report">
          <h2>能力分析报告</h2>
          
          {/* 整体评价 */}
          <section>
            <h3>📊 整体评价</h3>
            <p>{result.overall_assessment}</p>
          </section>
          
          {/* 优势领域 */}
          <section>
            <h3>✅ 优势领域</h3>
            {result.strengths.map((s, i) => (
              <div key={i} className="strength-item">🟢 {s}</div>
            ))}
          </section>
          
          {/* 薄弱环节 */}
          <section>
            <h3>⚠️ 薄弱环节</h3>
            {result.weaknesses.map((w, i) => (
              <div key={i} className="weakness-item">🟡 {w}</div>
            ))}
          </section>
          
          {/* 知识缺口 */}
          <section>
            <h3>🎯 知识缺口</h3>
            {result.knowledge_gaps.map((gap, i) => (
              <div key={i} className="knowledge-gap">
                <h4>
                  {gap.priority === 'high' ? '🔴' : gap.priority === 'medium' ? '🟡' : '🟢'}
                  {gap.topic}
                </h4>
                <p>{gap.description}</p>
                <ul>
                  {gap.recommendations.map((rec, j) => (
                    <li key={j}>{rec}</li>
                  ))}
                </ul>
              </div>
            ))}
          </section>
          
          {/* 能力验证 */}
          <section>
            <h3>🎯 能力级别验证</h3>
            <p>
              声称级别: {result.proficiency_verification.claimed_level}
              <br />
              实际级别: {result.proficiency_verification.verified_level}
              ({result.proficiency_verification.confidence})
            </p>
            <p>{result.proficiency_verification.reasoning}</p>
          </section>
        </div>
      )}
    </div>
  );
};
```

## 总结

这个功能为用户提供了深度的能力剖析，帮助他们：
1. ✅ 了解自己的真实水平
2. ✅ 发现知识盲区
3. ✅ 获得针对性学习建议
4. ✅ 生成更个性化的学习路线图

前端只需要调用两个API端点，即可完成从评估到分析的完整流程。

