# CurriculumArchitectAgent 提示词优化报告

## 优化概述

**优化时间**: 2026年2月2日  
**优化对象**: `backend/prompts/curriculum_architect.j2`  
**优化目标**: 基于成功的提示词模板重构现有提示词，提升模型输出质量

## 优化前后对比

### 优化前的问题

1. **过度简化**
   - Prompt 只有 89 行，过于简洁
   - 缺少足够的上下文信息
   - 硬编码结构要求（强制 4×2×3 = 24 个 Concept）

2. **缺少关键信息注入**
   - 没有注入用户画像（学习动机、职业背景）
   - 没有注入需求分析结果（技能差距、个性化建议）
   - 没有明确的语言偏好说明

3. **设计原则不明确**
   - 没有说明渐进式难度设计
   - 没有时间分配指导
   - 没有主题合并策略

4. **示例不足**
   - 只有1个简化的示例
   - 示例不够完整和真实

### 优化后的改进

#### 1. 丰富的上下文注入（2. Context Injection）

**注入的信息**:
```jinja2
- 用户学习目标：{{ user_goal }}
- 需求分析结果：
  * 解析后的目标：{{ parsed_goal }}
  * 关键技术栈：{{ key_technologies | join(", ") }}
  * 难度画像：{{ difficulty_profile }}
  * 时间约束：{{ time_constraint }}
  * 推荐学习重点：{{ recommended_focus | join("; ") }}
  * 用户画像：{{ user_profile_summary }}
  * 技能差距：{{ skill_gap_analysis | join("; ") }}
  * 个性化建议：{{ personalized_suggestions | join("; ") }}

用户画像：
- 当前水平：{{ current_level }}
- 职业背景：{{ career_background }}
- 每周可投入时间：{{ available_hours_per_week }} 小时
- 学习动机：{{ motivation }}

语言偏好设置：
- 主要语言：{{ primary_language }}
- 次要语言：{{ secondary_language }}
```

#### 2. 灵活的结构要求（3. Constraints & Rules）

**优化前**:
```
- Stage 数量: 恰好 4 个
- 每个 Stage: 恰好 2 个 Module
- 每个 Module: 恰好 3 个 Concept
```

**优化后**:
```
1. Stage（阶段）数量：严格控制在 3-5 个之间
   - 3 个：适用于聚焦单一技能栈的短期目标
   - 4 个：适用于中等复杂度的技能学习
   - 5 个：适用于较复杂的综合技能

2. Module（模块）数量：每个 Stage 包含 2-4 个 Module

3. Concept（概念）数量：每个 Module 包含 3-6 个 Concept
```

#### 3. 明确的设计原则

新增以下设计原则：

1. **渐进式难度**
   - Stage 1-2：基础知识和核心概念
   - Stage 3-4：进阶技能和实际应用
   - Stage 5（如有）：综合项目和生产实践

2. **合理的时间分配**
   - 简单概念（easy）：0.5-2 小时
   - 中等概念（medium）：2-4 小时
   - 困难概念（hard）：4-8 小时

3. **前置关系清晰**
   - prerequisites 只能引用已定义的 concept_id
   - 不能形成循环依赖

4. **主题合并策略**
   - 将相关性强的主题合并到同一 Stage
   - 例如："认证"和"授权"应该在同一 Stage

5. **难度分布合理**
   - 建议比例：easy 30%, medium 50%, hard 20%

#### 4. 详细的输出格式说明（4. Output Format）

新增：
- 明确的 JSON 结构说明
- 每个字段的详细要求
- 格式错误示例和正确示例
- 关键格式要求（禁止 Markdown、技术术语处理等）

#### 5. 质量检查清单（5. Quality Checklist）

新增 18 项自检清单，确保输出质量：
- [ ] Stage 数量是否在 3-5 个之间？
- [ ] 每个 Stage 的时长是否相对均衡？
- [ ] 难度是否渐进？
- [ ] `total_estimated_hours` 是否等于所有 Concept 的时长之和？
- [ ] `recommended_completion_weeks` 是否基于用户的每周可投入时间计算？
- ... (共18项)

## 代码改动

### 1. Prompt 模板优化

**文件**: `backend/prompts/curriculum_architect.j2`

**改动**:
- 从 89 行扩展到 168 行
- 从 ~1.5KB 增加到 ~4.5KB
- 增加了大量的上下文变量和设计指导

### 2. Agent 代码重构

**文件**: `backend/app/agents/curriculum_architect.py`

**主要改动**:

#### 新增方法：`_prepare_prompt_context`

```python
def _prepare_prompt_context(self, input_data: CurriculumDesignInput) -> dict:
    """
    准备 Prompt 模板的上下文变量
    
    返回包含所有模板变量的字典：
    - 用户目标和需求分析（9个字段）
    - 用户画像（4个字段）
    - 语言偏好（2个字段）
    - Roadmap ID（1个字段）
    """
```

#### 修改方法：`execute`

```python
# 优化前
system_prompt = self._load_system_prompt("curriculum_architect.j2")
user_message = self._build_user_message(input_data)
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_message},
]

# 优化后
prompt_context = self._prepare_prompt_context(input_data)
system_prompt = self._load_system_prompt("curriculum_architect.j2", **prompt_context)
messages = [
    {"role": "system", "content": system_prompt},
]
```

**改动说明**:
- 移除了独立的 user message
- 所有信息都整合到 system prompt 中
- 通过模板变量注入上下文，使 prompt 更加结构化

## 测试验证

### 测试脚本增强

**文件**: `backend/scripts/test_curriculum_architect.py`

**新增功能**:
1. Prompt 渲染检查和调试
2. 渲染后的 Prompt 保存到文件
3. Prompt 预览（前 500 字符）

### 测试结果

**Prompt 渲染成功** ✅
- Prompt 长度: 4479 字符
- 所有模板变量正确填充
- 格式清晰、结构完整

**示例渲染输出**:
```
[1. Role Definition]
你是课程架构师，负责设计结构化的学习路线图框架...

[2. Context Injection]
当前任务上下文：
- 用户学习目标：成为 Python Web 开发工程师
- 需求分析结果：
  * 解析后的目标：学习 Python Web 开发，能够独立开发和部署...
  * 关键技术栈：Python, FastAPI, SQLAlchemy, PostgreSQL, Docker, Redis
  * 难度画像：中级难度，需要扎实的 Python 基础和数据库知识
  ...

[3. Constraints & Rules]
工作规范：
**🔴 [CRITICAL] Roadmap ID 约束：**
你**必须**使用以下 roadmap_id（不要修改或生成新的）：
roadmap_id: python-web-dev-fastapi-2024-test-001
...

[4. Output Format]
...

[5. Quality Checklist]
...
```

## 优化效果总结

### 定量指标

| 指标 | 优化前 | 优化后 | 提升 |
|-----|-------|-------|-----|
| Prompt 行数 | 89 | 168 | +89% |
| Prompt 大小 | ~1.5KB | ~4.5KB | +200% |
| 上下文变量数 | 0 | 16 | +∞ |
| 设计原则数 | 0 | 6 | +∞ |
| 质量检查项 | 6 | 18 | +200% |

### 定性改进

1. **上下文更丰富** ✅
   - 完整的用户画像注入
   - 详细的需求分析结果
   - 个性化建议和技能差距分析

2. **结构更灵活** ✅
   - 从固定的 4×2×3 改为 3-5 个 Stage 的灵活范围
   - 支持根据任务复杂度调整结构

3. **指导更明确** ✅
   - 详细的设计原则
   - 具体的时间分配指导
   - 明确的难度分布建议

4. **格式更规范** ✅
   - 详细的 JSON 格式说明
   - 明确的字段要求
   - 错误示例和正确示例对比

5. **质量有保障** ✅
   - 18 项自检清单
   - 关键约束重点标记
   - 输出前质量验证

## 预期效果

基于成功的提示词模板，优化后的 Prompt 预期能够：

1. **提升输出质量**
   - 更准确地理解用户需求
   - 生成更符合用户水平的课程架构
   - 更合理的时间分配和难度设计

2. **增强个性化**
   - 根据用户画像调整起点
   - 根据技能差距设计重点
   - 根据学习动机优化路径

3. **改善结构合理性**
   - 渐进式难度设计
   - 合理的主题合并
   - 清晰的前置关系

4. **提高格式正确性**
   - 符合 JSON Schema 要求
   - 避免 Markdown 格式错误
   - 确保所有字段完整

## 后续建议

### 短期（立即可行）

1. **使用更强大的模型进行测试**
   - 建议使用 Claude 3.5 Sonnet 或 GPT-4
   - 验证优化后的 Prompt 在强模型上的表现

2. **收集真实案例数据**
   - 用真实的用户需求测试
   - 评估输出质量和满意度

### 中期（功能增强）

1. **添加 Few-shot 示例**
   - 在 Prompt 中加入 2-3 个完整的示例
   - 展示不同复杂度的路线图设计

2. **优化模板变量**
   - 简化模板语法
   - 增加条件逻辑（如根据水平调整提示）

### 长期（持续优化）

1. **建立 Prompt 版本管理**
   - 追踪不同版本的效果
   - A/B 测试不同 Prompt 设计

2. **自动化质量评估**
   - 建立输出质量评分系统
   - 自动检测常见问题

## 附录

### 相关文件

1. **优化后的 Prompt 模板**
   - `backend/prompts/curriculum_architect.j2`

2. **Agent 实现**
   - `backend/app/agents/curriculum_architect.py`

3. **测试脚本**
   - `backend/scripts/test_curriculum_architect.py`

4. **测试输出**
   - `backend/scripts/test_rendered_prompt.txt` (渲染后的完整 Prompt)

### 测试命令

```bash
# 诊断当前配置
python scripts/test_curriculum_architect.py --diagnose

# 使用默认配置测试
python scripts/test_curriculum_architect.py

# 查看渲染后的 Prompt
cat scripts/test_rendered_prompt.txt
```

---

**优化人员**: AI Assistant  
**文档创建时间**: 2026-02-02 00:18  
**文档位置**: `backend/docs/20260202_CurriculumArchitectAgent提示词优化报告.md`
