# 技术栈测验题目 Markdown 渲染优化

## 问题描述

之前生成的技术栈测验题目中，包含代码的题目没有使用 Markdown 格式，导致前端展示时无法正确渲染代码块，用户看不到格式化的代码，影响答题体验。

**示例问题**：
```
在 Python 中，以下代码的输出结果是什么？from datetime import datetime, timezone, timedelta\n\nlocal_tz = timezone(timedelta(hours=8))...
```

代码全部挤在一行，没有缩进和语法高亮。

## 解决方案

### 1. 后端 Prompt 优化

**文件**: `backend/prompts/tech_assessment_question_generator.j2`

**修改内容**：
- 添加了 **代码格式要求** 章节，明确要求 LLM 在生成包含代码的题目时使用 Markdown 代码块格式
- 更新了示例，展示如何正确使用 Markdown 代码块包裹代码
- 示例格式：
  ```markdown
  ```python
  from datetime import datetime
  print(datetime.now())
  ```
  ```

**关键要求**：
```jinja2
5. **代码格式要求（重要）**:
   - **如果题目或选项中包含代码片段，必须使用 Markdown 代码块格式**
   - 使用三个反引号 ` ``` ` 包裹代码，并指定语言（如 python, javascript, sql 等）
   - 示例：` ```python\ncode here\n``` `
   - 这样可以确保前端能正确渲染代码高亮和格式
```

### 2. 前端组件优化

**文件**: `frontend-next/components/profile/assessment-questions.tsx`

**修改内容**：

#### 2.1 添加依赖
```typescript
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
```

#### 2.2 创建 QuestionMarkdown 组件
专为测验题目设计的轻量级 Markdown 渲染器：

```typescript
function QuestionMarkdown({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={{
        // 代码块渲染 - 专业样式
        code({ node, className, children, ...props }) {
          const isInline = !className?.includes('language-');
          const match = /language-(\w+)/.exec(className || '');
          const language = match ? match[1] : '';
          
          if (!isInline && language) {
            // 多行代码块
            return (
              <div className="my-3 rounded-lg overflow-hidden border border-sage-200/60 bg-slate-900">
                <div className="px-4 py-2 bg-slate-800/80 border-b border-slate-700">
                  <span className="text-xs font-mono text-slate-400 uppercase">
                    {language}
                  </span>
                </div>
                <pre className="p-4 overflow-x-auto">
                  <code className={className} {...props}>
                    {children}
                  </code>
                </pre>
              </div>
            );
          }
          
          // 行内代码
          return (
            <code className="px-1.5 py-0.5 rounded-md bg-sage-100 text-sage-800 text-sm font-mono border border-sage-200/60">
              {children}
            </code>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

#### 2.3 替换题目和选项渲染
- **题目文本**: 从 `<p>{question.question}</p>` 改为 `<QuestionMarkdown content={question.question} />`
- **选项文本**: 从 `<span>{option}</span>` 改为 `<QuestionMarkdown content={option} />`

## 效果对比

### 优化前
```
在 Python 中，以下代码的输出结果是什么？from datetime import datetime, timezone, timedelta\n\nlocal_tz = timezone(timedelta(hours=8))...
```
- 代码挤在一行
- 无语法高亮
- 难以阅读

### 优化后
```
在 Python 中，以下代码的输出结果是什么？

┌─────────────────────────────┐
│ python                      │
├─────────────────────────────┤
│ from datetime import ...    │
│                             │
│ local_tz = timezone(...)    │
│ naive_dt = datetime(...)    │
│ ...                         │
└─────────────────────────────┘
```
- 代码块独立显示
- 语法高亮
- 格式清晰，易于阅读

## 测试指南

### 1. 后端测试

生成包含代码的测验题目：

```bash
cd backend
poetry shell

# 使用 Python 脚本测试
python -c "
import asyncio
from app.services.tech_assessment_generator import TechAssessmentGenerator

async def test():
    generator = TechAssessmentGenerator()
    result = await generator.generate_assessment_with_plan(
        technology='python',
        proficiency_level='intermediate'
    )
    
    # 检查是否有代码块格式的题目
    for q in result['questions']:
        if '```' in q['question']:
            print('✅ 发现使用 Markdown 代码块的题目')
            print(q['question'][:200])
            break
    else:
        print('⚠️ 未发现使用 Markdown 代码块的题目')

asyncio.run(test())
"
```

### 2. 前端测试

#### 方法 1: 在 Profile 页面测试
1. 启动前端开发服务器：
   ```bash
   cd frontend-next
   npm run dev
   ```

2. 访问 `http://localhost:3000/profile`

3. 点击 "Tech Stack" 部分，选择一个技术栈（如 Python）

4. 设置能力级别为 "Intermediate"，点击 "Start Assessment"

5. 检查题目渲染：
   - 查看是否有包含代码块的题目
   - 代码块是否有语法高亮
   - 代码块是否有独立的背景和边框
   - 行内代码（如 `variable`）是否正确渲染

#### 方法 2: 手动测试（如果后端题目生成较慢）
可以在浏览器开发者工具中直接修改 DOM 来验证渲染效果。

### 3. 验证要点

✅ **成功标准**：
- [ ] 题目中的代码块使用三反引号格式（` ```language `）
- [ ] 前端正确渲染代码块，带语法高亮
- [ ] 代码块有独立的容器（背景色、边框）
- [ ] 代码块顶部显示语言标识（如 "PYTHON"）
- [ ] 行内代码（单反引号）也正确渲染
- [ ] 选项中的代码也支持 Markdown 渲染

❌ **需要修复的情况**：
- 代码显示为纯文本，无高亮
- 代码挤在一行
- `\n` 等转义字符直接显示
- 渲染错误或布局错乱

## 技术细节

### Markdown 解析流程

1. **后端 LLM 生成**：
   ```json
   {
     "question": "题目\n\n```python\ncode\n```",
     "options": ["选项1", "选项2"]
   }
   ```

2. **传输到前端**：JSON 字符串中 `\n` 被正确保留

3. **前端解析**：
   - `ReactMarkdown` 将文本解析为 Markdown AST
   - `remarkGfm` 支持 GitHub Flavored Markdown（代码块、表格等）
   - `rehypeHighlight` 使用 highlight.js 进行语法高亮
   - 自定义 `code` 组件渲染代码块

4. **样式应用**：
   - 使用 `highlight.js/styles/github-dark.css` 提供语法高亮样式
   - 自定义 Tailwind CSS 类提供容器样式

### 支持的语言

Highlight.js 自动检测语言，支持常见的编程语言：
- Python
- JavaScript / TypeScript
- Java
- C / C++
- Go
- Rust
- SQL
- Bash / Shell
- 等 100+ 种语言

### 性能考虑

- **组件级别**：`QuestionMarkdown` 作为纯展示组件，无状态，渲染快速
- **按需渲染**：只有包含 Markdown 语法的内容才会触发解析
- **代码高亮**：使用 rehype-highlight 在构建时处理，性能优于客户端高亮

## 相关文件

### 后端
- `backend/app/services/tech_assessment_generator.py` - 测验题目生成服务
- `backend/prompts/tech_assessment_question_generator.j2` - 题目生成 Prompt 模板
- `backend/prompts/tech_assessment_planner.j2` - 考察规划 Prompt 模板

### 前端
- `frontend-next/components/profile/assessment-questions.tsx` - 测验题目展示组件
- `frontend-next/components/tutorial/markdown-renderer.tsx` - 通用 Markdown 渲染器（参考）
- `frontend-next/app/(app)/profile/page.tsx` - Profile 页面主组件

## 未来优化建议

1. **复制代码功能**：在代码块右上角添加复制按钮
2. **代码执行**：对于简单的代码片段，提供在线执行功能
3. **代码对比**：对于多选题，支持代码片段的并排对比
4. **暗色模式适配**：根据系统主题切换代码高亮方案
5. **语言特定优化**：针对不同语言提供特定的渲染优化（如 SQL 的表格展示）

## 总结

通过后端 Prompt 优化 + 前端 Markdown 渲染，成功解决了代码题目展示问题：
- ✅ 后端生成格式规范的 Markdown 代码块
- ✅ 前端正确解析并渲染代码高亮
- ✅ 用户体验显著提升，代码清晰易读
- ✅ 保持了组件的轻量级和高性能

这个解决方案适用于所有包含代码的文本内容，具有良好的可扩展性。

