# Datetime时区处理最佳实践

> **经验等级**: ⚠️ 高危陷阱  
> **首次遇到**: 2026-02-08  
> **影响范围**: PostgreSQL + SQLAlchemy + Pydantic  
> **典型错误**: `can't subtract offset-naive and offset-aware datetimes`

---

## 🎯 核心原则

**PostgreSQL `TIMESTAMP WITHOUT TIME ZONE` 要求datetime对象必须无时区信息（tzinfo=None）**

---

## ⚠️ 常见错误模式

### 错误1: 使用 `datetime.now()`

```python
# ❌ 错误：生成带时区的datetime
from datetime import datetime

class QuizGenerationOutput(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)  # ❌ 带时区
```

**错误原因**:
- `datetime.now()` 返回本地时区的datetime，带有`tzinfo`属性
- PostgreSQL的`TIMESTAMP WITHOUT TIME ZONE`不接受带时区的datetime
- asyncpg驱动在类型检查时抛出`DBAPIError`

### 错误2: 时区不一致

```python
# ❌ 错误：Pydantic模型和SQLAlchemy模型使用不同的时间函数
# Pydantic模型
class OutputModel(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)  # 带时区

# SQLAlchemy模型
class DBModel(SQLModel, table=True):
    created_at: datetime = Field(
        default_factory=beijing_now,  # 无时区
        sa_column=Column(DateTime(timezone=False))
    )
```

---

## ✅ 正确做法

### 1. 项目级时间工厂函数

**定义**（`backend/app/models/database.py`）：
```python
from datetime import datetime, timezone, timedelta

# 北京时区 (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

def beijing_now() -> datetime:
    """
    获取当前北京时间（无时区信息）
    
    返回的datetime对象不包含时区信息，但值是北京时间。
    这样存入PostgreSQL的TIMESTAMP WITHOUT TIME ZONE时不会被转换。
    """
    utc_now = datetime.now(timezone.utc)
    beijing_time = utc_now + timedelta(hours=8)
    return beijing_time.replace(tzinfo=None)  # ⚠️ 移除时区信息
```

### 2. Pydantic模型统一使用beijing_now

```python
# ✅ 正确：Domain模型导入并使用beijing_now
from app.models.database import beijing_now

class QuizGenerationOutput(BaseModel):
    created_at: datetime = Field(default_factory=beijing_now, ...)
    
class TutorialGenerationOutput(BaseModel):
    created_at: datetime = Field(default_factory=beijing_now, ...)
    
class ResourceRecommendationOutput(BaseModel):
    created_at: datetime = Field(default_factory=beijing_now, ...)
```

### 3. SQLAlchemy模型统一使用beijing_now

```python
# ✅ 正确：数据库模型使用beijing_now + DateTime(timezone=False)
class QuizMetadata(SQLModel, table=True):
    created_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False)),  # ⚠️ 必须是timezone=False
        description="创建时间（北京时间）"
    )
    updated_at: datetime = Field(
        default_factory=beijing_now,
        sa_column=Column(DateTime(timezone=False)),
        description="最后更新时间（北京时间）"
    )
```

### 4. CRUD层防御性处理

```python
# ✅ 最佳实践：CRUD保存前确保时区正确
from datetime import datetime, timezone, timedelta

def _ensure_naive_datetime(dt: datetime) -> datetime:
    """
    确保datetime对象无时区信息（防御性函数）
    
    防止未来有人传入带时区的datetime导致数据库错误。
    """
    if dt.tzinfo is None:
        return dt  # 已经无时区，直接返回
    
    # 有时区信息，转换为北京时间并移除时区
    BEIJING_TZ = timezone(timedelta(hours=8))
    beijing_time = dt.astimezone(BEIJING_TZ)
    return beijing_time.replace(tzinfo=None)


class QuizCRUD(BaseCRUD):
    async def save_quiz(self, session, quiz_output, roadmap_id):
        metadata = QuizMetadata(
            quiz_id=quiz_output.quiz_id,
            concept_id=quiz_output.concept_id,
            created_at=_ensure_naive_datetime(quiz_output.created_at),  # ✅ 防御性转换
        )
        session.add(metadata)
        await session.flush()
        return metadata
```

---

## 🔍 排查清单

遇到时区相关错误时，按此顺序检查：

- [ ] **错误信息确认**  
  是否包含`can't subtract offset-naive and offset-aware datetimes`

- [ ] **Domain模型检查**  
  所有Output模型的`created_at`是否使用`beijing_now()`

- [ ] **数据库模型检查**  
  SQLAlchemy列定义是否为`DateTime(timezone=False)`

- [ ] **CRUD层检查**  
  保存前是否调用`_ensure_naive_datetime()`进行防御性转换

- [ ] **导入检查**  
  Domain模型是否导入了`from app.models.database import beijing_now`

---

## 🧪 测试验证

### 单元测试模板

```python
from datetime import datetime, timezone, timedelta
from app.models.domain import QuizGenerationOutput
from app.crud.crud_quiz import _ensure_naive_datetime

def test_output_model_timezone():
    """验证Output模型生成的datetime无时区"""
    quiz = QuizGenerationOutput(
        concept_id="test",
        quiz_id="test-id",
        questions=[...],
        total_questions=1,
    )
    
    # 验证created_at无时区
    assert quiz.created_at.tzinfo is None, "created_at不应该有时区信息"


def test_ensure_naive_datetime():
    """验证防御性转换函数"""
    # 测试1: 无时区datetime
    naive_dt = datetime(2024, 6, 15, 12, 0)
    result = _ensure_naive_datetime(naive_dt)
    assert result.tzinfo is None
    assert result == naive_dt
    
    # 测试2: UTC时区datetime
    utc_dt = datetime(2024, 6, 15, 4, 0, tzinfo=timezone.utc)
    result = _ensure_naive_datetime(utc_dt)
    assert result.tzinfo is None
    assert result.hour == 12  # UTC 4:00 = 北京时间 12:00
```

---

## 📚 参考文档

### PostgreSQL时区处理
- `TIMESTAMP WITH TIME ZONE`: 存储UTC时间，查询时转换为客户端时区
- `TIMESTAMP WITHOUT TIME ZONE`: 按字面值存储，不做时区转换

### Python datetime
- `datetime.now()`: 返回本地时区datetime（带tzinfo）
- `datetime.utcnow()`: 返回UTC时间（无tzinfo，已废弃）
- `datetime.now(timezone.utc)`: 返回UTC时间（带tzinfo，推荐）

### SQLAlchemy 2.0
- `DateTime(timezone=True)`: 映射到`TIMESTAMP WITH TIME ZONE`
- `DateTime(timezone=False)`: 映射到`TIMESTAMP WITHOUT TIME ZONE`

---

## 🚨 历史案例

### 案例1: 内容生成元数据保存失败（2026-02-08）

**问题**:
```
sqlalchemy.exc.DBAPIError: invalid input for query argument $9: 
datetime.datetime(2024, 6, 15, 12, 0, tz... 
(can't subtract offset-naive and offset-aware datetimes)
```

**根因**:
- 5个Agent Output模型使用`datetime.now()`
- 生成带时区的datetime
- 与数据库`TIMESTAMP WITHOUT TIME ZONE`冲突

**修复**:
- Domain模型改用`beijing_now()`
- CRUD层添加`_ensure_naive_datetime()`防御
- 影响文件：8个

**教训**:
- Domain模型和Database模型必须使用相同的时间工厂函数
- CRUD层需要防御性编程，即使Domain模型正确

---

## 🛡️ 预防措施

### 代码审查要点

```python
# ❌ 审查时拒绝以下代码
created_at: datetime = Field(default_factory=datetime.now)
created_at: datetime = Field(default_factory=datetime.utcnow)
created_at: datetime = Field(default_factory=lambda: datetime.now())

# ✅ 审查时接受以下代码
created_at: datetime = Field(default_factory=beijing_now)
```

### Linter规则（可选）

```python
# pylint: disable=datetime-now-without-timezone
# 或配置pre-commit hook检查datetime.now()的使用
```

### 文档约定

在`backend/app/models/database.py`开头必须包含：
```python
"""
时间处理说明：
- 所有时间字段统一使用北京时间 (UTC+8)
- 使用 TIMESTAMP WITHOUT TIME ZONE 存储，避免 PostgreSQL 自动转换为 UTC
- beijing_now() 返回无时区信息的北京时间
"""
```

---

## 💡 关键要点

1. **一致性至上**: Domain、Database、CRUD三层必须使用相同的时间函数
2. **防御性编程**: 即使Domain层正确，CRUD层仍需验证
3. **类型匹配**: Pydantic的datetime必须与SQLAlchemy的DateTime(timezone=X)匹配
4. **文档先行**: 在database.py开头明确时间处理规范
5. **测试验证**: 添加单元测试确保时区处理正确
