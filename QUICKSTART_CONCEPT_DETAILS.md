# 快速开始：测试Concept详情页Quiz和Resources功能

## 前提条件

1. 后端服务正在运行（默认端口：8000）
2. 前端服务正在运行（默认端口：3000）
3. 数据库中已有roadmap数据

## 步骤1：启动服务

### 后端
```bash
cd backend
./scripts/start_dev.sh
```

### 前端
```bash
cd frontend-next
npm run dev
```

## 步骤2：找到可用的roadmap_id和concept_id

### 方法1：通过数据库查询
```sql
-- 查找最近的roadmap
SELECT roadmap_id, title 
FROM roadmap_metadata 
ORDER BY created_at DESC 
LIMIT 5;

-- 查看roadmap中的concepts（假设roadmap_id是'rm-xxx'）
SELECT 
    roadmap_id,
    framework_data->'stages'->0->'modules'->0->'concepts'->0->>'concept_id' as concept_id,
    framework_data->'stages'->0->'modules'->0->'concepts'->0->>'name' as concept_name
FROM roadmap_metadata 
WHERE roadmap_id = 'rm-xxx';
```

### 方法2：通过API查询
```bash
# 获取roadmap列表（如果有的话）
curl http://localhost:8000/api/v1/roadmaps/{roadmap_id}

# 响应中会包含完整的stages->modules->concepts结构
```

## 步骤3：测试后端API

使用测试脚本：
```bash
cd backend

# 替换为实际的roadmap_id和concept_id
uv run python scripts/test_concept_details_api.py rm-abc123 concept-xyz
```

期望输出：
```
================================================================================
Testing Concept Details API
Roadmap ID: rm-abc123
Concept ID: concept-xyz
================================================================================

1. Testing Quiz API...
✅ Quiz API Success
   Quiz ID: quiz-123
   Total Questions: 5
   Easy: 2, Medium: 2, Hard: 1
   Generated At: 2024-01-01T00:00:00

   Sample Question:
   - Type: single_choice
   - Question: What is HTML?...
   - Options: 4 options
   - Difficulty: easy

2. Testing Resources API...
✅ Resources API Success
   Resources ID: res-456
   Resources Count: 3
   Generated At: 2024-01-01T00:00:00

   Sample Resource:
   - Title: MDN Web Docs
   - Type: documentation
   - URL: https://developer.mozilla.org/...
   - Relevance: 0.95
   - Description: Complete HTML reference...
```

## 步骤4：测试前端页面

1. 打开浏览器访问：
```
http://localhost:3000/app/roadmap/{roadmap_id}/learn/{concept_id}
```

2. 验证页面功能：

### Tutorial标签页
- [ ] 显示教程内容
- [ ] 目录导航正常工作
- [ ] Markdown渲染正确

### Quiz标签页
- [ ] 显示题目列表
- [ ] 可以选择答案
- [ ] 提交按钮在选完所有题后激活
- [ ] 提交后显示正确/错误标记
- [ ] 显示答案解析
- [ ] 显示得分
- [ ] 可以重新测验

### Resources标签页
- [ ] 显示资源卡片
- [ ] 资源类型标签正确
- [ ] 相关度显示正确
- [ ] 点击可以打开外部链接

## 步骤5：测试空状态

### 测试没有Quiz的concept
```bash
# 使用一个没有生成quiz的concept_id访问页面
# 应该显示："暂无测验"占位提示
```

### 测试没有Resources的concept
```bash
# 使用一个没有生成resources的concept_id访问页面
# 应该显示："暂无学习资源"占位提示
```

## 步骤6：测试错误处理

### 测试不存在的concept
```bash
# 访问一个不存在的concept_id
http://localhost:3000/app/roadmap/{roadmap_id}/learn/invalid-concept-id

# 应该显示："加载失败"错误页面
```

### 测试后端服务停止
```bash
# 1. 停止后端服务
# 2. 刷新前端页面
# 3. 应该显示加载失败并提示连接错误
```

## 故障排查

### 问题1：前端一直显示加载中
**排查步骤：**
1. 打开浏览器开发者工具（F12）
2. 查看Console标签是否有错误
3. 查看Network标签，检查API请求状态
4. 确认后端服务是否正在运行

### 问题2：Quiz或Resources显示"暂无"
**可能原因：**
1. 数据库中确实没有生成这些数据
2. concept_id不匹配

**解决方法：**
```bash
# 检查数据库
SELECT * FROM quiz_metadata WHERE concept_id = 'your-concept-id';
SELECT * FROM resource_recommendation_metadata WHERE concept_id = 'your-concept-id';

# 如果没有数据，需要生成
# 使用完整的roadmap生成流程，或者单独生成quiz和resources
```

### 问题3：后端API返回404
**排查步骤：**
```bash
# 直接测试API
curl http://localhost:8000/api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz

# 检查返回的错误信息
# 常见原因：
# - concept_id错误
# - roadmap_id错误
# - 数据未生成
```

## 生成测试数据（如果需要）

如果数据库中没有quiz和resources数据，可以通过以下方式生成：

### 方法1：使用完整流式生成
```python
# 创建一个新的roadmap，会自动生成所有内容
# 使用前端的roadmap创建页面，或者API调用
```

### 方法2：为现有roadmap生成内容
```bash
cd backend

# 为整个roadmap生成tutorials、quiz和resources
uv run python scripts/generate_tutorials_for_roadmap.py {roadmap_id}
```

### 方法3：单独生成quiz或resources
```python
# 通过API端点单独生成
POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz/regenerate
POST /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources/regenerate

# 需要提供user_id和preferences
```

## 验收标准

✅ **必须通过的检查项**

1. [ ] 后端API正常返回quiz数据（200状态码）
2. [ ] 后端API正常返回resources数据（200状态码）
3. [ ] 前端页面可以正常加载
4. [ ] Quiz标签页显示题目并可以答题
5. [ ] Resources标签页显示资源列表
6. [ ] 空状态正确显示占位提示
7. [ ] 错误状态正确显示错误信息
8. [ ] 加载状态显示加载动画

## 示例：完整的测试流程

```bash
# 1. 启动服务
cd backend && ./scripts/start_dev.sh &
cd frontend-next && npm run dev &

# 2. 找到一个可用的roadmap（从数据库或API）
export ROADMAP_ID="rm-abc123"
export CONCEPT_ID="concept-html-basics"

# 3. 测试后端API
cd backend
uv run python scripts/test_concept_details_api.py $ROADMAP_ID $CONCEPT_ID

# 4. 打开浏览器测试前端
# 访问：http://localhost:3000/app/roadmap/$ROADMAP_ID/learn/$CONCEPT_ID

# 5. 手动验证所有功能
# - Tutorial加载 ✓
# - Quiz显示并可答题 ✓
# - Resources显示 ✓
# - 空状态正确 ✓
# - 错误处理正确 ✓
```

## 性能检查

使用浏览器开发者工具检查：

1. **Network标签**
   - API请求时间 < 1秒
   - 并行请求（tutorial、quiz、resources）
   - 没有重复请求

2. **Performance标签**
   - 页面加载时间 < 3秒
   - 没有内存泄漏
   - React组件渲染次数合理

3. **Console标签**
   - 没有警告或错误
   - 日志信息清晰

## 下一步

功能验证通过后，可以考虑：

1. **增加测试覆盖**
   - 单元测试
   - 集成测试
   - E2E测试

2. **性能优化**
   - 添加数据缓存
   - 实现预加载
   - 优化渲染性能

3. **功能增强**
   - 保存答题记录
   - 资源评分
   - 个性化推荐

## 参考文档

- 详细实现文档：`CONCEPT_DETAILS_IMPLEMENTATION.md`
- API文档：后端`/docs`端点
- 前端组件：`frontend-next/app/app/roadmap/[id]/learn/[conceptId]/page.tsx`

