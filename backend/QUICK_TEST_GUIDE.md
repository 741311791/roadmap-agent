# 🚀 新API端点快速测试指南

## 1分钟快速开始

### 步骤1：启动服务 (终端1)

```bash
cd backend
uvicorn app.main:app --reload
```

等待看到：
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### 步骤2：运行测试 (终端2)

```bash
cd backend
python scripts/test_new_api_endpoints.py
```

### 预期结果

如果一切正常，你会看到：

```
================================================================================
新API端点测试脚本
================================================================================

测试时间: 2025-12-05 22:00:00
基础URL: http://localhost:8000

================================================================================
测试1: 健康检查端点
================================================================================
✅ 请求成功: 200

[... 更多测试 ...]

================================================================================
测试结果汇总
================================================================================
总测试数: 12
✅ 通过: 12
❌ 失败: 0
成功率: 100.0%

🎉 所有测试通过！新API端点工作正常！
```

---

## 📋 完整测试清单

### 测试的端点

```
✅ POST   /api/v1/roadmaps/generate              # 创建生成任务
✅ GET    /api/v1/roadmaps/{task_id}/status      # 查询任务状态
✅ GET    /api/v1/roadmaps/{roadmap_id}          # 获取路线图
✅ GET    /api/v1/roadmaps/{roadmap_id}/active-task
✅ GET    /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials
✅ GET    /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorials/latest
✅ GET    /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/resources
✅ GET    /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/quiz
✅ POST   /api/v1/roadmaps/{task_id}/approve
✅ POST   /api/v1/roadmaps/{roadmap_id}/retry-failed
✅ POST   /api/v1/roadmaps/{roadmap_id}/concepts/{concept_id}/tutorial/modify
✅ GET    /health                                 # 健康检查
✅ GET    /openapi.json                          # API文档
```

---

## 🔍 手动测试示例

### 使用curl测试

```bash
# 1. 健康检查
curl http://localhost:8000/health

# 2. 创建路线图生成任务
curl -X POST http://localhost:8000/api/v1/roadmaps/generate \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user",
    "session_id": "test-session",
    "preferences": {
      "learning_goal": "学习Python基础",
      "available_hours_per_week": 10,
      "motivation": "兴趣学习",
      "current_level": "beginner",
      "career_background": "学生",
      "content_preference": ["text", "hands_on"]
    },
    "additional_context": "快速入门"
  }'

# 3. 查询任务状态（使用上面返回的task_id）
curl http://localhost:8000/api/v1/roadmaps/{task_id}/status

# 4. 获取OpenAPI文档
curl http://localhost:8000/openapi.json | python -m json.tool
```

### 使用浏览器测试

1. **Swagger UI**  
   访问: http://localhost:8000/docs
   
2. **ReDoc**  
   访问: http://localhost:8000/redoc

3. **健康检查**  
   访问: http://localhost:8000/health

---

## ❌ 常见问题

### 问题1: 连接被拒绝

**错误信息**:
```
httpx.ConnectError: [Errno 61] Connection refused
```

**解决方案**:
```bash
# 检查服务是否运行
curl http://localhost:8000/health

# 如果没有响应，启动服务
uvicorn app.main:app --reload
```

### 问题2: 端口已被占用

**错误信息**:
```
ERROR: [Errno 48] Address already in use
```

**解决方案**:
```bash
# 查找占用端口的进程
lsof -i :8000

# 杀死进程
kill -9 <PID>

# 或使用不同端口
uvicorn app.main:app --reload --port 8001
```

### 问题3: 导入错误

**错误信息**:
```
ModuleNotFoundError: No module named 'app'
```

**解决方案**:
```bash
# 设置PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 或从backend目录运行
cd backend
python scripts/test_new_api_endpoints.py
```

---

## 📊 测试结果解读

### 成功的测试

```
✅ 请求成功: 200
响应摘要: {"status": "healthy", "version": "1.0.0"}
```

**含义**: 端点正常工作，返回了预期的数据

### 资源不存在（正常）

```
⚠️  资源不存在（404）- 这在测试环境是正常的
```

**含义**: 端点正常工作，但测试数据不存在（这是预期的）

### 请求失败

```
❌ 请求失败: 500
错误详情: {"detail": "Internal server error"}
```

**含义**: 端点有问题，需要检查服务器日志

---

## 🎯 下一步

测试通过后：

1. ✅ **验证所有端点工作正常**
2. 📋 **查看详细文档**
   - `backend/tests/api/README.md`
   - `backend/docs/TESTING_NEW_API.md`
3. 🔧 **运行完整pytest测试**
   ```bash
   pytest backend/tests/api/test_new_endpoints_e2e.py -v
   ```
4. 🚀 **准备部署**
   - 备份旧代码
   - 删除旧文件
   - 提交更改

---

## 📚 相关文档

- [API端点README](tests/api/README.md)
- [完整测试文档](docs/TESTING_NEW_API.md)
- [测试完成报告](docs/API_TESTING_COMPLETE.md)
- [阶段二总结](docs/PHASE2_COMPLETION_SUMMARY.md)

---

## 💡 提示

- 🟢 绿色 ✅ = 测试通过
- 🟡 黄色 ⚠️  = 警告（通常是正常的）
- 🔴 红色 ❌ = 测试失败

**大多数404错误在测试环境中是正常的！**

重点关注：
- 端点是否能响应
- HTTP状态码是否正确
- 服务是否稳定运行

---

**快速帮助**: 如有问题，查看 `backend/docs/TESTING_NEW_API.md` 的常见问题章节
