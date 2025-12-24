# 技术栈动态选择和自定义功能

## 功能概述

Profile页面中的Current Tech Stack下拉列表现在支持：
1. **动态加载**：从数据库`tech_stack_assessments`表中获取所有有测验题目的技术栈
2. **自定义输入**：用户可以输入自定义技术栈名称
3. **自动生成测验**：对于自定义技术栈，系统会在后台生成测验题目

## 实现细节

### Backend 变更

#### 1. Repository层 (`app/db/repositories/tech_assessment_repo.py`)

新增方法 `get_available_technologies()`:
```python
async def get_available_technologies(self) -> List[str]:
    """获取所有有测验题目的技术栈列表（去重）"""
    from sqlalchemy import distinct
    
    result = await self.session.execute(
        select(distinct(TechStackAssessment.technology)).order_by(
            TechStackAssessment.technology
        )
    )
    
    technologies = [row[0] for row in result.all()]
    return technologies
```

#### 2. API端点 (`app/api/v1/endpoints/tech_assessment.py`)

新增端点 `GET /api/v1/tech-assessments/available-technologies`:
```python
@router.get("/available-technologies", response_model=AvailableTechnologiesResponse)
async def get_available_technologies(db: AsyncSession = Depends(get_db)):
    """获取所有有测验题目的技术栈列表"""
    repo = TechAssessmentRepository(db)
    technologies = await repo.get_available_technologies()
    
    return AvailableTechnologiesResponse(
        technologies=technologies,
        count=len(technologies),
    )
```

响应格式：
```json
{
  "technologies": ["angular", "aws", "docker", "python", "react"],
  "count": 5
}
```

### Frontend 变更

#### 1. API客户端 (`lib/api/endpoints.ts`)

新增方法：
```typescript
export async function getAvailableTechnologies(): Promise<{
  technologies: string[];
  count: number;
}> {
  const response = await apiClient.get('/tech-assessments/available-technologies');
  return response.data;
}
```

#### 2. Profile页面 (`app/(app)/profile/page.tsx`)

**关键变更：**

1. **加载可用技术栈列表**：
   - 页面加载时并行获取用户画像和可用技术栈列表
   - 存储在`availableTechnologies`状态中

2. **TechStackRow组件更新**：
   - 接收`availableTechnologies`作为props
   - **只显示数据库中有测验题目的技术栈**（不再显示预定义的固定列表）
   - 提供"+ 自定义技术栈"选项，允许用户输入任意技术栈名称
   - 自定义输入支持：
     - Enter键确认
     - Escape键取消
     - 自动转换为小写

3. **标签显示优化**：
   - 使用`getTechLabel()`函数提供友好的显示名称
   - 预定义技术栈显示其标准标签（如"Python", "React"等）
   - 自定义技术栈首字母大写显示

## 用户交互流程

### 1. 选择已有技术栈
1. 用户点击技术栈下拉框
2. 看到所有数据库中有测验题目的技术栈列表（已排序）
3. 选择一个技术栈
4. 点击"Assess"按钮可以立即开始测验

### 2. 添加自定义技术栈
1. 用户点击技术栈下拉框
2. 选择"+ 自定义技术栈"
3. 输入自定义技术栈名称（如"hive", "spark"等）
4. 按Enter确认或按Escape取消
5. 点击"Assess"按钮
6. **首次使用**：系统提示"正在为 {tech} 生成测验题库，预计需要1-2分钟..."
7. **后续使用**：题库生成完成后，直接显示测验题目

## 技术栈生成流程

当用户对自定义技术栈进行测验时：

1. 前端调用 `GET /tech-assessments/{technology}/{proficiency}`
2. 如果数据库中不存在该技术栈的题库：
   - 返回404错误
3. 前端调用 `POST /tech-assessments/custom`：
   ```json
   {
     "technology": "hive",
     "proficiency": "intermediate"
   }
   ```
4. Backend检查题库是否存在：
   - 如果存在所有3个级别（beginner/intermediate/expert），直接返回题目
   - 如果不存在，触发后台任务生成题库
5. 后台任务使用`TechAssessmentGenerator`为3个级别各生成20道题目
6. 生成完成后，用户可以刷新页面重新进行测验

## 数据流

```
用户打开Profile页面
    ↓
并行请求:
  1. GET /users/{userId}/profile
  2. GET /tech-assessments/available-technologies
    ↓
显示技术栈下拉列表（仅数据库中有题目的）
    ↓
用户选择技术栈 或 输入自定义技术栈
    ↓
保存到用户画像
    ↓
点击"Assess"按钮
    ↓
调用测验API (已有题库) 或 自定义测验API (需要生成)
```

## 注意事项

1. **权限控制**：
   - 所有API端点都需要用户认证
   - 用户只能修改自己的画像

2. **性能考虑**：
   - 可用技术栈列表会在页面加载时缓存
   - 数据库查询使用了索引（technology字段）
   - 使用`distinct()`去重，避免重复数据

3. **错误处理**：
   - 如果获取可用技术栈失败，fallback到空列表
   - 自定义技术栈生成是后台异步任务，不会阻塞UI

4. **UX优化**：
   - 已选择的技术栈在下拉列表中显示为禁用状态
   - 自定义输入框自动聚焦
   - 支持键盘快捷键（Enter/Escape）

## 测试建议

1. **功能测试**：
   - 验证下拉列表只显示数据库中的技术栈
   - 测试自定义输入流程
   - 测试自定义技术栈的测验生成

2. **边界测试**：
   - 空技术栈列表
   - 特殊字符输入
   - 超长技术栈名称

3. **性能测试**：
   - 大量技术栈时的下拉列表性能
   - 并发生成多个自定义技术栈

## 相关文件

### Backend
- `backend/app/db/repositories/tech_assessment_repo.py`
- `backend/app/api/v1/endpoints/tech_assessment.py`
- `backend/app/models/database.py` (TechStackAssessment模型)

### Frontend
- `frontend-next/app/(app)/profile/page.tsx`
- `frontend-next/lib/api/endpoints.ts`
- `frontend-next/components/profile/tech-assessment-dialog.tsx`

## 未来改进建议

1. **搜索功能**：在下拉列表中添加搜索过滤
2. **标签分组**：按技术类别分组（前端、后端、数据库等）
3. **热门推荐**：显示最受欢迎的技术栈
4. **同步状态**：实时显示自定义技术栈的生成进度
5. **批量导入**：允许用户一次性导入多个技术栈

