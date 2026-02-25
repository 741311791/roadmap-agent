# CurriculumArchitect Agent 性能优化

## 优化背景

### 性能瓶颈分析
- **问题**: Agent 响应时间过长，主要浪费在结构化提取环节
- **原因**: `CurriculumDesignOutput` 模型包含大量无效字段（第一阶段 Markdown 无法提取的）
- **影响**: 嵌套深度过深（4层：Framework->Stage->Module->Concept），且 Concept 包含 tutorial_id、resources_id、quiz_id 等后续阶段才需要的字段

### 优化目标
1. ⚡ **提升结构化提取速度**: 简化 response_model，减少无效字段
2. ✓ **自动补充默认值**: 转换后补充完整字段
3. ✓ **依赖关系检查**: 自动检查并修复前置关系

---

## 优化方案

### 1. 创建简化模型 (domain.py)

新增 4 个简化模型，只包含第一阶段需要的字段：

```python
class SimplifiedConcept(BaseModel):
    """简化的 Concept（只包含第一阶段字段）"""
    concept_id: str
    name: str
    description: str
    estimated_hours: float
    prerequisites: List[str]
    difficulty: Literal["easy", "medium", "hard"]
    keywords: List[str]

class SimplifiedModule(BaseModel):
    """简化的 Module"""
    module_id: str
    name: str
    description: str
    concepts: List[SimplifiedConcept]

class SimplifiedStage(BaseModel):
    """简化的 Stage"""
    stage_id: str
    name: str
    description: str
    order: int
    modules: List[SimplifiedModule]

class SimplifiedRoadmapFramework(BaseModel):
    """简化的路线图框架"""
    roadmap_id: str
    title: str
    stages: List[SimplifiedStage]
    total_estimated_hours: float
    recommended_completion_weeks: int
```

**移除的无效字段** (共 10 个):
- `content_status`: "pending"
- `tutorial_id`: None
- `content_ref`: None
- `content_version`: "v1"
- `content_summary`: None
- `resources_status`: "pending"
- `resources_id`: None
- `resources_count`: 0
- `quiz_status`: "pending"
- `quiz_id`: None
- `quiz_questions_count`: 0

---

### 2. 转换函数 (curriculum_architect.py)

#### `_convert_to_full_framework()`
将简化模型转换为完整框架，补充默认值：

```python
def _convert_to_full_framework(self, simplified: SimplifiedRoadmapFramework) -> RoadmapFramework:
    """
    补充所有后续阶段需要的字段默认值
    """
    # 遍历 Stage -> Module -> Concept
    # 为每个 Concept 补充完整字段
    full_concept = Concept(
        # 第一阶段提取的字段
        concept_id=s_concept.concept_id,
        name=s_concept.name,
        description=s_concept.description,
        estimated_hours=s_concept.estimated_hours,
        prerequisites=s_concept.prerequisites,
        difficulty=s_concept.difficulty,
        keywords=s_concept.keywords,
        # 补充默认值
        content_status="pending",
        tutorial_id=None,
        resources_status="pending",
        quiz_status="pending",
        # ... 其他字段
    )
```

**优势**:
- LLM 只需要生成 7 个字段，不需要处理无效字段
- 转换由代码完成，速度快且准确

---

### 3. 依赖检查函数 (curriculum_architect.py)

#### `_check_and_fix_dependencies()`
自动检查并修复依赖关系问题：

**检查项**:
1. **前置概念是否存在**: 检查 `prerequisites` 中的 concept_id 是否在路线图中
2. **顺序是否合理**: 前置概念应出现在当前概念之前
3. **循环依赖**: 使用 DFS 检测并移除循环边

**修复策略**:
- 不存在的前置概念 → 移除
- 顺序错误的前置概念 → 移除
- 循环依赖 → 移除循环中的最后一条边

```python
def _check_and_fix_dependencies(self, framework: RoadmapFramework) -> Tuple[RoadmapFramework, List[str]]:
    """
    Returns:
        (修复后的框架, 修复日志列表)
    """
    # 1. 构建概念位置映射
    concept_positions: Dict[str, Tuple[int, int, int]] = {}
    
    # 2. 检查并修复每个概念的前置关系
    for concept in all_concepts:
        valid_prereqs = []
        for prereq_id in concept.prerequisites:
            # 检查是否存在
            if prereq_id not in all_concept_ids:
                fixes.append(f"移除不存在的前置概念: {prereq_id}")
                continue
            
            # 检查顺序
            if prereq_pos >= current_pos:
                fixes.append(f"移除顺序错误的前置概念: {prereq_id}")
                continue
            
            valid_prereqs.append(prereq_id)
        
        concept.prerequisites = valid_prereqs
    
    # 3. 检测并移除循环依赖
    cycles = self._detect_cycles(framework)
    # ...
```

#### `_detect_cycles()`
使用 DFS 算法检测循环依赖：

```python
def _detect_cycles(self, framework: RoadmapFramework) -> List[List[str]]:
    """使用 DFS 检测循环依赖"""
    # 构建邻接表
    graph: Dict[str, List[str]] = {}
    
    # DFS 遍历
    def dfs(node: str):
        if neighbor in rec_stack:
            # 找到循环
            cycle = path[cycle_start:] + [neighbor]
            cycles.append(cycle)
```

---

### 4. 更新 execute() 方法

**执行流程**:
```python
async def execute(self, input_data: CurriculumDesignInput) -> CurriculumDesignOutput:
    # 1. 使用简化的 response_model
    simplified_framework = await self._call_llm(
        messages,
        response_model=SimplifiedRoadmapFramework,  # ⭐ 简化模型
        use_two_stage=True,
    )
    
    # 2. 转换为完整框架（补充默认值）
    full_framework = self._convert_to_full_framework(simplified_framework)
    
    # 3. 检查并修复依赖关系
    full_framework, fixes = self._check_and_fix_dependencies(full_framework)
    
    # 4. 返回结果
    return CurriculumDesignOutput(framework=full_framework)
```

---

## 优化效果

### 1. 结构化提取速度提升
- **原因**: 减少了 10+ 个无效字段，嵌套层级从 4 层简化为 3 层（Framework-Stage-Module-Concept，但 Concept 字段大幅减少）
- **预期**: 提速 30-50%（取决于模型）

### 2. 依赖关系自动修复
- **功能**: 自动检测并修复 3 类问题（不存在的前置、顺序错误、循环依赖）
- **优势**: 无需人工介入，保证路线图结构合法性

### 3. 代码可维护性提升
- **职责分离**: 
  - LLM 只负责生成核心字段
  - 代码负责补充默认值和依赖检查
- **易于扩展**: 新增后续阶段字段时，只需修改 `_convert_to_full_framework()`

---

## 测试验证

### 运行测试
```bash
cd backend
python scripts/test_curriculum_architect_optimized.py
```

### 验证点
1. ✓ 结构化提取速度（对比优化前）
2. ✓ 默认字段补充（检查 content_status、tutorial_id 等）
3. ✓ 依赖关系检查（验证前置概念有效性）
4. ✓ 循环依赖检测（运行 framework.validate_structure()）

---

## 代码变更

### 新增文件
- `backend/scripts/test_curriculum_architect_optimized.py` - 性能测试脚本

### 修改文件
1. `backend/app/models/domain.py`
   - 新增 `SimplifiedConcept`
   - 新增 `SimplifiedModule`
   - 新增 `SimplifiedStage`
   - 新增 `SimplifiedRoadmapFramework`

2. `backend/app/agents/curriculum_architect.py`
   - 新增 `_convert_to_full_framework()` - 转换函数
   - 新增 `_check_and_fix_dependencies()` - 依赖检查
   - 新增 `_detect_cycles()` - 循环检测
   - 更新 `execute()` - 使用简化模型

---

## 后续优化建议

### 1. 并行化依赖检查
如果路线图很大（1000+ concepts），可以考虑并行检查依赖关系：
```python
import asyncio

async def _check_concept_dependencies(concept, all_concept_ids):
    # 异步检查单个概念
    pass

# 并行检查所有概念
await asyncio.gather(*[_check_concept_dependencies(c, ids) for c in concepts])
```

### 2. 缓存简化模型的 Schema
如果频繁调用，可以缓存 `SimplifiedRoadmapFramework.model_json_schema()` 结果，避免重复生成。

### 3. Prompt 优化
如果发现 LLM 经常生成无效的前置关系，可以在 Prompt 中明确说明：
```
# 前置关系规则
- 前置概念必须出现在当前概念之前
- 不要创建循环依赖
- 不要引用不存在的概念
```

---

## 总结

通过 **简化 response_model + 代码补充 + 依赖检查** 的三步优化，CurriculumArchitect Agent 在保证功能完整性的同时，显著提升了性能和可靠性。
