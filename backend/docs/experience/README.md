# 经验知识库 (Experience Knowledge Base)

本目录收录项目开发过程中遇到的**高频易错问题**和**最佳实践**，旨在：
1. 避免重复踩坑
2. 加速新成员上手
3. 建立团队技术规范

---

## 📚 文档分类

### 🔥 高危陷阱（必读）
这类问题具有以下特征：
- 错误信息难以理解
- 涉及底层原理（Event Loop、数据库驱动、进程模型）
- 修复不当会导致更严重的问题
- 容易在代码审查中被忽略

**当前文档**:
1. `asyncio_event_loop_in_celery.md` - AsyncIO在Celery中的使用规范
2. `datetime_timezone_best_practices.md` - Datetime时区处理最佳实践

---

## 🎯 使用指南

### 何时查阅
1. **遇到相似错误时**  
   根据错误信息关键词（如`bound to a different event loop`）查找对应文档

2. **新增功能时**  
   - 新增Celery任务 → 查阅`asyncio_event_loop_in_celery.md`
   - 新增Agent Output → 查阅`datetime_timezone_best_practices.md`

3. **代码审查时**  
   使用文档中的检查清单验证PR

### 如何贡献

遇到新的高频错误时，按以下模板创建经验文档：

```markdown
# [问题主题]

> **经验等级**: [🔥极高危 / ⚠️高危 / 📌中危]
> **首次遇到**: [日期]
> **影响范围**: [技术栈组合]
> **典型错误**: [错误信息关键词]

## 🎯 核心原则
[一句话总结最佳实践]

## 🧪 底层原理
[解释为什么会出现这个问题]

## ⚠️ 错误模式分析
[展示典型错误代码]

## ✅ 正确做法
[展示正确代码]

## 🚨 历史案例
[记录项目中真实遇到的案例]

## 🔍 排查清单
[提供检查要点]

## 💡 关键要点
[总结5-7条核心要点]
```

---

## 📖 文档索引

### 按技术栈分类

#### AsyncIO & 并发
- `asyncio_event_loop_in_celery.md` - Celery中的Event Loop管理

#### 数据库 & ORM
- `datetime_timezone_best_practices.md` - 时区处理规范

#### 待补充
- LangGraph Checkpointer最佳实践
- SQLAlchemy Session生命周期管理
- Redis缓存策略
- Agent Prompt设计规范

### 按错误类型分类

#### RuntimeError
- `asyncio_event_loop_in_celery.md` → `bound to a different event loop`

#### DBAPIError
- `datetime_timezone_best_practices.md` → `can't subtract offset-naive and offset-aware datetimes`

---

## 🔄 更新策略

### 何时更新文档
1. **发现新的错误模式** → 更新对应文档的"错误模式分析"章节
2. **找到更好的解决方案** → 更新"正确做法"章节
3. **添加新的历史案例** → 更新"历史案例"章节
4. **补充测试验证** → 更新"测试验证"章节

### 版本控制
- 每次重大更新在文档顶部添加"更新日志"
- 保留历史案例，不要删除（即使问题已解决）

---

## 🎓 学习路径

对于新加入的开发者：

1. **第一周**: 精读所有🔥极高危文档
2. **第二周**: 浏览所有⚠️高危文档
3. **开发前**: 根据功能类型查阅相关文档
4. **遇到错误**: 优先在experience目录搜索解决方案

---

## 📞 联系方式

如果文档无法解决问题：
1. 查看`backend/docs/`下的具体修复记录
2. 查看git历史中的相关commit
3. 咨询团队成员

---

**最后更新**: 2026-02-08  
**文档数量**: 2个  
**覆盖错误类型**: RuntimeError, DBAPIError
