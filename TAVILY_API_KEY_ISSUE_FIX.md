# Tavily API Key 配置问题修复指南

**问题发现日期**: 2025-12-09

## 问题描述

测试脚本 `test_tavily_sdk_integration.py` 报错提示 Tavily API 配额已用完，但直接使用 `test_tavily.py` 脚本却可以正常工作。

## 根本原因

通过诊断脚本 `diagnose_tavily_settings.py` 发现：

1. **环境变量中的 API Key**: `tvly-dev-lSNr0Ss9KlH...` (已达到配额限制 ❌)
2. **.env 文件中的 API Key**: `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` (还有配额 ✅)

**优先级问题**：
- Pydantic Settings 读取配置的优先级：**环境变量 > .env 文件**
- 因此 `settings.TAVILY_API_KEY` 读取的是环境变量中已耗尽配额的旧 key
- 而 `test_tavily.py` 直接硬编码了 .env 文件中的新 key，所以可以正常工作

## 解决方案

### 方案 1：清除环境变量（推荐）

在终端中执行以下命令清除环境变量中的旧 key：

```bash
# 清除环境变量
unset TAVILY_API_KEY

# 验证已清除
echo $TAVILY_API_KEY  # 应该输出空行

# 重新加载 .env 文件
cd /Users/louie/Documents/Vibecoding/roadmap-agent/backend
source .env

# 验证新 key
echo $TAVILY_API_KEY  # 应该输出 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
```

### 方案 2：更新环境变量

直接在终端中设置新的 API Key：

```bash
export TAVILY_API_KEY="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"

# 验证
echo $TAVILY_API_KEY
```

### 方案 3：永久修复（彻底解决）

如果环境变量是在 shell 配置文件中设置的，需要修改配置文件：

#### 对于 zsh (macOS 默认)：

```bash
# 编辑 ~/.zshrc
nano ~/.zshrc

# 查找并删除或更新以下行：
# export TAVILY_API_KEY="旧的key"

# 保存后重新加载
source ~/.zshrc
```

#### 对于 bash：

```bash
# 编辑 ~/.bashrc 或 ~/.bash_profile
nano ~/.bashrc

# 查找并删除或更新 TAVILY_API_KEY 相关行

# 保存后重新加载
source ~/.bashrc
```

## 验证修复

执行以下命令验证修复是否成功：

```bash
cd /Users/louie/Documents/Vibecoding/roadmap-agent/backend

# 运行诊断脚本
source .venv/bin/activate
python scripts/diagnose_tavily_settings.py
```

**期望输出**：
- ✅ 环境变量中的 key 应该是 `tvly-dev-ero1FNHxisnulgwMsaa9IPnhP0...`
- ✅ API 调用测试应该成功，而不是配额限制错误

## 测试修复效果

修复后，重新运行测试脚本：

```bash
cd /Users/louie/Documents/Vibecoding/roadmap-agent/backend
source .venv/bin/activate
python scripts/test_tavily_sdk_integration.py
```

应该能够成功执行所有测试。

## 预防措施

为了避免将来再次出现类似问题，建议：

### 1. 统一配置管理

只在 `.env` 文件中配置 API Key，避免在 shell 配置文件中设置：

```bash
# ✅ 推荐：只在 .env 文件中配置
# backend/.env
TAVILY_API_KEY=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

# ❌ 避免：在 ~/.zshrc 或 ~/.bashrc 中设置
```

### 2. 添加配置验证

在项目启动时验证 API Key 配置：

```python
# app/config/settings.py
from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    TAVILY_API_KEY: str
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 打印配置来源（仅用于调试）
        env_key = os.getenv("TAVILY_API_KEY")
        if env_key and env_key != self.TAVILY_API_KEY:
            print(f"⚠️ 警告：环境变量和 .env 文件中的 TAVILY_API_KEY 不一致")
```

### 3. 添加日志记录

在工具初始化时记录使用的 API Key（脱敏）：

```python
# app/tools/search/tavily_api_search.py
def __init__(self):
    super().__init__(tool_id="tavily_api_search")
    self.api_key = settings.TAVILY_API_KEY
    # 记录 API Key 前缀（用于调试）
    logger.debug(
        "tavily_api_tool_initialized",
        api_key_prefix=self.api_key[:20] if self.api_key else "None"
    )
```

## 总结

- **问题根因**：环境变量优先级高于 .env 文件，导致读取了错误的 API Key
- **快速修复**：执行 `unset TAVILY_API_KEY` 清除环境变量
- **长期方案**：统一使用 .env 文件管理配置，避免在 shell 配置文件中设置敏感信息
- **验证工具**：使用 `diagnose_tavily_settings.py` 诊断配置问题

---

**修复完成后，请删除此文件或将其移至文档目录。**

