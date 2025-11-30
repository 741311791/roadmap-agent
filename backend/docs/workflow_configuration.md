# 工作流配置说明

## 环境变量配置

系统有三个主要的工作流控制开关：

1. **SKIP_STRUCTURE_VALIDATION** (默认: false)
   - 是否跳过结构验证（Structure Validator）和路线图编辑（Roadmap Editor）

2. **SKIP_HUMAN_REVIEW** (默认: false)  
   - 是否跳过人工审核（Human Review）

3. **SKIP_TUTORIAL_GENERATION** (默认: false)
   - 是否跳过教程生成（Tutorial Generator）

## 工作流路由逻辑

### 场景 1: SKIP_STRUCTURE_VALIDATION = true

```
Intent Analysis → Curriculum Design → [根据其他配置决定下一步]

- 如果 SKIP_HUMAN_REVIEW = true:
  - 如果 SKIP_TUTORIAL_GENERATION = true:
    - 流程: Intent Analysis → Curriculum Design → END
  - 如果 SKIP_TUTORIAL_GENERATION = false:
    - 流程: Intent Analysis → Curriculum Design → Tutorial Generation → END
    
- 如果 SKIP_HUMAN_REVIEW = false:
  - 流程: Intent Analysis → Curriculum Design → Human Review → [根据审核结果]
    - approved: Tutorial Generation (如果 SKIP_TUTORIAL_GENERATION = false) 或 END
    - modify: Roadmap Edit (如果 SKIP_STRUCTURE_VALIDATION = false) 或 Curriculum Design
```

### 场景 2: SKIP_STRUCTURE_VALIDATION = false (默认)

```
Intent Analysis → Curriculum Design → Structure Validation → [根据验证结果]

验证失败且未达到最大重试次数:
  → Roadmap Edit → Structure Validation (循环)

验证通过或达到最大重试次数:
  → [根据其他配置决定下一步]
  
  - 如果 SKIP_HUMAN_REVIEW = true:
    - 如果 SKIP_TUTORIAL_GENERATION = true:
      - 流程: → END
    - 如果 SKIP_TUTORIAL_GENERATION = false:
      - 流程: → Tutorial Generation → END
      
  - 如果 SKIP_HUMAN_REVIEW = false:
    - 流程: → Human Review → [根据审核结果]
      - approved: Tutorial Generation (如果 SKIP_TUTORIAL_GENERATION = false) 或 END
      - modify: Roadmap Edit → Structure Validation (循环)
```

## 重要结论

**当 SKIP_HUMAN_REVIEW = true 时，教程生成不会被跳过！**

只要 `SKIP_TUTORIAL_GENERATION = false`（默认值），教程生成步骤会正常执行：

- **SKIP_STRUCTURE_VALIDATION = true + SKIP_HUMAN_REVIEW = true**
  - 流程：Intent Analysis → Curriculum Design → **Tutorial Generation** → END ✓
  
- **SKIP_STRUCTURE_VALIDATION = false + SKIP_HUMAN_REVIEW = true**
  - 流程：Intent Analysis → Curriculum Design → Structure Validation → **Tutorial Generation** → END ✓

## 当前环境配置

根据之前的检查，当前环境设置为：
```
SKIP_HUMAN_REVIEW=True
SKIP_TUTORIAL_GENERATION=False
```

这意味着：
- ✓ 会跳过人工审核步骤
- ✓ **会执行教程生成步骤**
- ✓ 工作流自动完成，无需人工干预

## 注意事项

如果您希望跳过教程生成，需要显式设置：
```bash
export SKIP_TUTORIAL_GENERATION=true
```

如果三个开关都设置为 true：
```bash
export SKIP_STRUCTURE_VALIDATION=true
export SKIP_HUMAN_REVIEW=true
export SKIP_TUTORIAL_GENERATION=true
```

则工作流会变成最简化版本：
```
Intent Analysis → Curriculum Design → END
```

仅生成路线图框架，不生成教程内容。

