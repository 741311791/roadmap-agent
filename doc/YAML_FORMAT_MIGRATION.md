# Curriculum Architect 输出格式迁移：文本格式 → YAML 格式

**迁移日期**: 2025-12-07  
**原因**: 正则表达式解析不可靠，容易因格式细微差异导致失败

---

## 📋 问题背景

### 旧方案的问题
1. **正则表达式不可靠**: Module 格式稍有变化（如缺少括号中的描述）就会解析失败
2. **难以调试**: 解析错误时难以快速定位问题
3. **代码复杂**: `_parse_compact_roadmap` 函数长达 255 行，包含大量正则表达式
4. **维护困难**: 需要维护多种边界情况和格式变体

### 新方案的优势
1. **结构化解析**: YAML 是标准格式，解析库成熟稳定
2. **易于调试**: YAML 语法错误有明确的错误信息和行号
3. **代码简洁**: 解析函数从 255 行减少到 65 行
4. **可维护性强**: 不需要维护复杂的正则表达式

---

## 🔧 修改内容

### 1. Prompt 修改 (`backend/prompts/curriculum_architect.j2`)

#### 修改前（文本格式）
```
===ROADMAP START===
ROADMAP_ID: python-web-dev
TITLE: Python Web开发完整学习路线
TOTAL_HOURS: 120
WEEKS: 8

Stage 1: 基础知识（掌握Python语法和Web基础概念）[30小时]
  Module 1.1: Python核心语法（学习Python编程基础）
    - Concept: 变量与数据类型（理解基本数据结构和变量声明）[2小时]
    - Concept: 控制流程（掌握条件判断和循环语句）[3小时]
...
===ROADMAP END===
```

#### 修改后（YAML 格式）
```yaml
roadmap_id: python-web-dev
title: Python Web开发完整学习路线
total_estimated_hours: 120
recommended_completion_weeks: 8
design_rationale: 设计说明

stages:
  - stage_id: stage-1
    name: 基础知识
    description: 掌握Python语法和Web基础概念
    order: 1
    modules:
      - module_id: mod-1-1
        name: Python核心语法
        description: 学习Python编程基础
        concepts:
          - concept_id: c-1-1-1
            name: 变量与数据类型
            description: 理解基本数据结构和变量声明
            estimated_hours: 2
            difficulty: easy
            keywords: [变量, 数据类型, 基础语法]
            prerequisites: []
```

**主要变化**:
- ✅ 移除 `===ROADMAP START/END===` 标记
- ✅ 使用标准 YAML 语法（2个空格缩进）
- ✅ 所有字段明确定义，没有隐式格式
- ✅ 时长从文本标注 `[2小时]` 改为结构化字段 `estimated_hours: 2`
- ✅ 新增必填字段：`difficulty`, `keywords`, `prerequisites`

### 2. 解析代码修改 (`backend/app/agents/curriculum_architect.py`)

#### 新增函数

**1. `_try_extract_yaml(content: str) -> str | None`**
- 从 LLM 输出中提取 YAML 内容
- 支持 ```yaml、``` 和裸 YAML 三种格式

**2. `_parse_yaml_roadmap(yaml_content: str) -> dict`**
- 使用 `yaml.safe_load()` 解析 YAML
- 自动补全可选字段（如 `total_estimated_hours`）
- 验证必填字段完整性
- 添加 concept 的默认字段（`content_status` 等）

#### 修改函数

**`_parse_compact_roadmap(content: str) -> dict`**
- **修改前**: 255 行，包含复杂的正则表达式和文本解析逻辑
- **修改后**: 65 行，简洁的格式检测和解析调用

```python
def _parse_compact_roadmap(content: str) -> dict:
    """解析路线图输出（支持 YAML、JSON）"""
    errors = {}
    
    # 1. 优先尝试 YAML 格式
    yaml_content = _try_extract_yaml(content)
    if yaml_content:
        try:
            return _parse_yaml_roadmap(yaml_content)
        except Exception as e:
            errors['yaml'] = str(e)
    
    # 2. 回退到 JSON 格式（兼容）
    json_content = _try_extract_json(content)
    if json_content:
        try:
            return _parse_json_roadmap(json_content)
        except Exception as e:
            errors['json'] = str(e)
    
    # 3. 所有格式都失败
    raise ValueError("无法解析路线图输出")
```

**优先级**:
1. YAML（推荐）
2. JSON（兼容旧输出）
3. ~~文本格式~~（已移除）

#### 导入修改
```python
# 添加
import yaml

# 移除（不再需要）
import re
```

### 3. 用户消息修改

**修改前**:
```
请以 JSON 格式返回结果，严格遵循输出 Schema。
```

**修改后**:
```
**重要**: 请以 YAML 格式返回结果，严格遵循 prompt 中定义的 YAML Schema 和示例格式。
```

---

## 📦 依赖变更

### 新增依赖
- `pyyaml` - Python YAML 解析库（应该已在 `pyproject.toml` 中）

### 验证依赖
```bash
cd backend
uv pip list | grep -i yaml
# 应该显示: PyYAML  x.x.x
```

如果未安装：
```bash
uv pip install pyyaml
```

---

## ✅ 测试方案

### 1. 单元测试（可选）

创建测试文件 `backend/tests/test_yaml_parsing.py`:

```python
import pytest
from app.agents.curriculum_architect import _parse_yaml_roadmap, _try_extract_yaml

def test_parse_simple_yaml():
    """测试基本 YAML 解析"""
    yaml_content = """
roadmap_id: test-roadmap
title: 测试路线图
total_estimated_hours: 10
recommended_completion_weeks: 2
design_rationale: 测试设计

stages:
  - stage_id: stage-1
    name: 测试阶段
    description: 测试描述
    order: 1
    modules:
      - module_id: mod-1-1
        name: 测试模块
        description: 模块描述
        concepts:
          - concept_id: c-1-1-1
            name: 测试概念
            description: 概念描述
            estimated_hours: 2
            difficulty: easy
            keywords: [测试, 关键词]
            prerequisites: []
    """
    
    result = _parse_yaml_roadmap(yaml_content)
    
    assert "framework" in result
    assert "design_rationale" in result
    assert result["framework"]["roadmap_id"] == "test-roadmap"
    assert len(result["framework"]["stages"]) == 1


def test_extract_yaml_from_code_block():
    """测试从代码块中提取 YAML"""
    content = """
Here is the roadmap:

```yaml
roadmap_id: test
title: Test
stages: []
```
    """
    
    yaml_content = _try_extract_yaml(content)
    assert yaml_content is not None
    assert "roadmap_id: test" in yaml_content
```

运行测试：
```bash
cd backend
pytest tests/test_yaml_parsing.py -v
```

### 2. 集成测试

**测试 1: 直接调用 Agent**

```bash
cd backend
python3 << 'EOF'
import asyncio
from app.agents.curriculum_architect import CurriculumArchitectAgent
from app.models.domain import IntentAnalysisOutput, LearningPreferences

async def test():
    agent = CurriculumArchitectAgent()
    
    intent = IntentAnalysisOutput(
        parsed_goal="学习Python",
        key_technologies=["Python", "Flask"],
        difficulty_profile="初级",
        time_constraint="2个月",
        recommended_focus=["基础语法", "Web开发"],
    )
    
    preferences = LearningPreferences(
        learning_goal="学习Python Web开发",
        current_level="beginner",
        available_hours_per_week=10,
        content_preference=["video", "practice"],
    )
    
    result = await agent.design(intent, preferences, "test-roadmap-001")
    print(f"✅ 成功生成路线图: {result.framework.title}")
    print(f"   阶段数: {len(result.framework.stages)}")
    print(f"   总时长: {result.framework.total_estimated_hours}小时")

asyncio.run(test())
EOF
```

**测试 2: 端到端测试**

```bash
cd backend
# 启动后端服务
uvicorn app.main:app --reload &

# 等待服务启动
sleep 5

# 发起请求（使用前端或 curl）
curl -X POST http://localhost:8000/api/v1/roadmap/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "learning_goal": "学习Python Web开发",
    "current_level": "beginner",
    "available_hours_per_week": 10
  }'
```

**预期结果**:
- ✅ 日志中显示 `parse_format_detected format="yaml"`
- ✅ 没有解析错误
- ✅ 返回的路线图结构完整

### 3. 错误场景测试

**测试 3: YAML 格式错误**

在 prompt 中故意引入 YAML 语法错误，验证错误处理：

```yaml
roadmap_id test  # 缺少冒号
title: 测试
```

**预期**:
- ✅ 日志中记录 `yaml_parse_error`
- ✅ 错误消息包含具体的 YAML 解析错误
- ✅ 回退到 JSON 格式尝试

---

## 🔍 调试指南

### 查看 LLM 原始输出

在日志中搜索以下事件：
```
curriculum_design_llm_response_received  # 包含 LLM 输出预览（前1000字符）
curriculum_design_llm_full_output        # 完整 LLM 输出（debug 级别）
```

### 查看解析过程

```
yaml_extracted_from_code_block           # YAML 从 ```yaml 块中提取
yaml_roadmap_parsed                      # YAML 解析成功
parse_format_detected format="yaml"      # 检测到 YAML 格式
```

### 查看错误

```
yaml_parse_error                         # YAML 解析失败
yaml_processing_error                    # YAML 处理失败
all_parse_formats_failed                 # 所有格式都失败
```

### 临时启用详细日志

修改 `backend/app/main.py` 或环境变量：
```python
import structlog

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.DEBUG),  # 改为 DEBUG
)
```

---

## 📊 性能对比

| 指标 | 旧方案（正则表达式） | 新方案（YAML） |
|------|---------------------|---------------|
| 代码行数 | 255 行 | 65 行 |
| 解析可靠性 | ⚠️ 中等（依赖格式严格匹配） | ✅ 高（标准库支持） |
| 错误信息 | ⚠️ 模糊 | ✅ 明确（行号+详情） |
| 维护成本 | ⚠️ 高（复杂正则） | ✅ 低（标准格式） |
| 扩展性 | ⚠️ 困难 | ✅ 容易 |
| 性能 | ~相当 | ~相当 |

---

## 🔄 回滚方案

如果新方案出现问题，可以临时回滚：

### 方案 A: Git 回滚（推荐）
```bash
git diff HEAD backend/app/agents/curriculum_architect.py > /tmp/yaml_changes.patch
git checkout HEAD -- backend/app/agents/curriculum_architect.py backend/prompts/curriculum_architect.j2
```

### 方案 B: 恢复旧函数
1. 从 git历史中恢复 `_parse_compact_text_roadmap` 函数
2. 在 `_parse_compact_roadmap` 中添加对文本格式的支持
3. 调整优先级：JSON → YAML → 文本

---

## 📝 后续优化建议

1. **添加 YAML Schema 验证**
   - 使用 `pydantic` 或 `jsonschema` 验证 YAML 结构
   - 在解析前验证，提供更友好的错误消息

2. **优化 Prompt**
   - 根据实际 LLM 输出情况调整示例
   - 添加更多边界情况的示例

3. **性能监控**
   - 添加解析时间指标
   - 监控不同格式的解析成功率

4. **单元测试覆盖**
   - 添加边界情况测试
   - 添加错误恢复测试

---

## 📚 参考资料

- [PyYAML 文档](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [YAML 规范](https://yaml.org/spec/1.2/spec.html)
- [YAML Lint 在线验证](https://www.yamllint.com/)

---

## ✅ 完成检查清单

- [x] 修改 prompt 输出格式为 YAML
- [x] 添加 `_try_extract_yaml()` 函数
- [x] 添加 `_parse_yaml_roadmap()` 函数  
- [x] 简化 `_parse_compact_roadmap()` 函数
- [x] 更新用户消息要求 YAML 输出
- [x] 移除不再使用的 `re` 导入
- [x] 添加 `yaml` 导入
- [x] 创建迁移文档
- [ ] 运行集成测试验证
- [ ] 监控生产环境日志

---

**迁移完成时间**: 2025-12-07 20:30  
**预计影响**: 提升解析可靠性，减少格式相关错误  
**风险等级**: 低（保留 JSON 格式作为回退）
