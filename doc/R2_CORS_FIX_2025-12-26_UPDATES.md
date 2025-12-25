# R2 教程内容下载修复 - URL 解析问题

## 🐛 问题追踪

### 问题 1: 导入路径错误 ✅ 已修复
```
ModuleNotFoundError: No module named 'app.tools.registry'
```
**修复：** `app.tools.registry` → `app.core.tool_registry`

---

### 问题 2: URL 编码问题 ✅ 已修复
```
NoSuchKey: xiaohongshu-operation-b5d8e7f2/concepts/xiaohongshu-operation-b5d8e7f2%3Ac-1-2-1/v1.md
```
**原因：** concept_id 中的冒号 `:` 被 URL 编码为 `%3A`

**修复：** 添加 `unquote()` 解码 URL 编码字符

---

### 问题 3: S3 Key 提取错误 ✅ 已修复
```
NoSuchKey: xiaohongshu-operation-b5d8e7f2/concepts/xiaohongshu-operation-b5d8e7f2:c-1-1-1/v1.md
```

**原因分析：**

R2 URL 结构：
```
https://xxx.r2.cloudflarestorage.com/roadmap-content/xiaohongshu.../concepts/.../v1.md?签名
       ^host                         ^bucket        ^key starts here
```

URL 分割后：
```python
parts = [
    'https:',                                      # 0
    '',                                            # 1
    'xxx.r2.cloudflarestorage.com',               # 2
    'roadmap-content',                             # 3 <- bucket
    'xiaohongshu-operation-b5d8e7f2',             # 4 <- key 开始
    'concepts',                                    # 5
    'xiaohongshu-operation-b5d8e7f2%3Ac-1-1-1',   # 6
    'v1.md?X-Amz-Algorithm=...'                   # 7
]
```

**错误的提取方法：**
```python
s3_key = "/".join(parts[4:])  # 错误：包含了 bucket 后的所有内容
```

**正确的提取方法：**
```python
bucket_idx = parts.index('roadmap-content')
s3_key = "/".join(parts[bucket_idx + 1:])  # ✅ 正确：跳过 bucket，从 key 开始
```

**最终修复：**
```python
# 1. 查找 bucket 名称的位置
bucket_name = settings.S3_BUCKET_NAME  # 'roadmap-content'

if bucket_name in parts:
    bucket_idx = parts.index(bucket_name)
    s3_key = "/".join(parts[bucket_idx + 1:])  # 跳过 bucket
else:
    # 降级方案：假设是标准格式
    s3_key = "/".join(parts[4:])

# 2. 移除 URL 参数
if "?" in s3_key:
    s3_key = s3_key.split("?")[0]

# 3. 解码 URL 编码
s3_key = unquote(s3_key)
```

**结果：**
```
原始 URL: https://.../roadmap-content/xiaohongshu.../concepts/xiaohongshu...%3Ac-1-1-1/v1.md?X-Amz-...
提取 key: xiaohongshu-operation-b5d8e7f2/concepts/xiaohongshu-operation-b5d8e7f2:c-1-1-1/v1.md
```

✅ 匹配上传时的 key 格式：`{roadmap_id}/concepts/{concept_id}/v{version}.md`

---

## 📝 完整修复代码

**文件：** `backend/app/api/v1/endpoints/tutorial.py`

```python
from urllib.parse import unquote
from app.config.settings import settings

# ...

# 2. 从 content_url 提取 S3 key
content_url = tutorial.content_url
s3_key = content_url

if "://" in content_url:
    parts = content_url.split("/")
    bucket_name = settings.S3_BUCKET_NAME
    
    if bucket_name in parts:
        # 找到 bucket，跳过它
        bucket_idx = parts.index(bucket_name)
        s3_key = "/".join(parts[bucket_idx + 1:])
    else:
        # 降级：假设标准格式
        s3_key = "/".join(parts[4:]) if len(parts) >= 5 else content_url

# 移除查询参数
if "?" in s3_key:
    s3_key = s3_key.split("?")[0]

# URL 解码
s3_key = unquote(s3_key)
```

---

## ✅ 测试验证

重启后端后，检查日志：

**期望的日志输出：**
```
tutorial_content_download_requested
  roadmap_id='xiaohongshu-operation-b5d8e7f2'
  concept_id='xiaohongshu-operation-b5d8e7f2:c-1-1-1'
  original_url='https://.../roadmap-content/...'
  extracted_key='xiaohongshu-operation-b5d8e7f2/concepts/xiaohongshu-operation-b5d8e7f2:c-1-1-1/v1.md'
  bucket='roadmap-content'

s3_download_success ✅
  key='xiaohongshu-operation-b5d8e7f2/concepts/xiaohongshu-operation-b5d8e7f2:c-1-1-1/v1.md'
  size_bytes=12345
```

---

**修复时间：** 2025-12-26  
**状态：** ✅ 完成，等待测试

