"""
应用配置（基于 pydantic-settings）

按时序图，配置包含以下角色的 LLM 设置：
- A1: 需求分析师 (ANALYZER_*)
- A2: 课程架构师 (ARCHITECT_*)
- A2E: 路线图编辑师 (EDITOR_*)
- A3: 结构审查员 (VALIDATOR_*)
- A4: 教程生成器 (GENERATOR_*)
- A5: 资源推荐师 (RECOMMENDER_*)
- A6: 测验生成器 (QUIZ_*)

内容修改相关 Agent 配置（独立于生成器）：
- 修改意图分析师 (MODIFICATION_ANALYZER_*)
- 教程修改师 (TUTORIAL_MODIFIER_*)
- 资源修改师 (RESOURCE_MODIFIER_*)
- 测验修改师 (QUIZ_MODIFIER_*)
"""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置"""

    _backend_dir = Path(__file__).resolve().parents[2]
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )
    
    # ==================== 应用配置 ====================
    ENVIRONMENT: str = Field("development", description="运行环境")
    DEBUG: bool = Field(False, description="调试模式")
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Learning Roadmap System"
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000",
        description="允许的跨域来源（逗号分隔的字符串）"
    )
    FEATURED_USER_ID: str = Field(
        "04005faa-fb45-47dd-a83c-969a25a77046",
        description="精选路线图归属用户 ID（固定 featured/admin 身份）"
    )
    FEATURED_USER_EMAIL: str = Field(
        "admin@example.com",
        description="精选路线图归属邮箱（主要用于初始化与一致性校验）"
    )
    FEATURED_ROADMAPS_CACHE_TTL_SECONDS: int = Field(
        300,
        description="精选路线图列表缓存 TTL（秒）"
    )
    
    @property
    def get_cors_origins(self) -> list[str]:
        """
        解析 CORS_ORIGINS 字符串为列表
        
        Returns:
            解析后的 CORS 来源列表
        """
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(',') if origin.strip()]
    
    # ==================== 数据库配置 ====================
    POSTGRES_HOST: str = Field("localhost", description="PostgreSQL 主机")
    POSTGRES_PORT: int = Field(5432, description="PostgreSQL 端口")
    POSTGRES_USER: str = Field("roadmap_user", description="数据库用户名")
    POSTGRES_PASSWORD: str = Field("roadmap_pass", description="数据库密码")
    POSTGRES_DB: str = Field("roadmap_db", description="数据库名称")
    
    # 连接池配置（4C8G 单机生产默认值）
    #
    # 设计目标：
    # - API、Celery、Redis 共用一台机器时，降低空闲常驻内存
    # - 保留适度突发能力，但避免每个进程都持有过大的连接池
    # - 需要更高吞吐时，优先通过环境变量覆盖，而不是继续放大默认值
    DB_POOL_SIZE: int = Field(
        3,
        description="数据库连接池基础大小（4C8G 单机生产默认值）"
    )
    DB_MAX_OVERFLOW: int = Field(
        2,
        description="数据库连接池最大溢出数（4C8G 单机生产默认值）"
    )
    LANGGRAPH_CHECKPOINTER_POOL_MIN_SIZE: int = Field(
        1,
        description="LangGraph Checkpointer 连接池最小连接数"
    )
    LANGGRAPH_CHECKPOINTER_POOL_MAX_SIZE: int = Field(
        3,
        description="LangGraph Checkpointer 连接池最大连接数（4C8G 单机生产默认值）"
    )
    
    @property
    def get_pool_config(self) -> dict:
        """
        根据运行环境动态返回数据库连接池配置
        
        说明：
        - 连接数直接取环境变量或字段默认值，避免“注释推荐值”和“实际生效值”不一致
        - 生产环境缩短 pool_recycle，尽早回收空闲连接
        
        Returns:
            连接池配置字典
        """
        if self.ENVIRONMENT == "production":
            return {
                "pool_size": self.DB_POOL_SIZE,
                "max_overflow": self.DB_MAX_OVERFLOW,
                "pool_recycle": 900,  # 15分钟
            }
        return {
            "pool_size": self.DB_POOL_SIZE,
            "max_overflow": self.DB_MAX_OVERFLOW,
            "pool_recycle": 1800,  # 30分钟
        }
    
    @property
    def DATABASE_URL(self) -> str:
        """
        构建异步数据库连接 URL
        
        基于单独的环境变量构建标准 PostgreSQL 连接字符串。
        """
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def CHECKPOINTER_DATABASE_URL(self) -> str:
        """
        构建 Checkpointer 数据库连接 URL
        
        LangGraph Checkpointer 使用的标准 PostgreSQL 连接字符串。
        """
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # ==================== S3/R2 对象存储配置 ====================
    S3_ENDPOINT_URL: str = Field("http://localhost:9000", description="S3 兼容端点（Cloudflare R2 或 MinIO）")
    S3_ACCESS_KEY_ID: str = Field("minioadmin", description="访问密钥 ID")
    S3_SECRET_ACCESS_KEY: str = Field("minioadmin123", description="访问密钥")
    S3_BUCKET_NAME: str = Field("roadmap-content", description="存储桶名称")
    S3_REGION: str | None = Field("auto", description="区域（R2 使用 'auto'，MinIO 可留空）")
    
    # ==================== Web Search 配置 ====================
    TAVILY_API_KEY: str | None = Field(None, description="Tavily API 密钥（可选，单个 Key）")
    TAVILY_API_KEY_LIST: str | None = Field(None, description="Tavily API Key 列表（逗号分隔或 JSON 数组格式，优先于 TAVILY_API_KEY）")
    TAVILY_RATE_LIMIT_PER_MINUTE: int = Field(100, description="Tavily API 速率限制（每分钟请求数，开发环境建议10，生产环境可设置100）")
    USE_DUCKDUCKGO_FALLBACK: bool = Field(True, description="是否使用 DuckDuckGo 作为备选搜索引擎")
    
    # ==================== API速率限制配置（全局IP级别）====================
    # 这些限制是针对整个应用的全局速率限制，而非单个请求
    # API厂商通常按IP识别并限制请求速率（RPM - Requests Per Minute）
    # 建议设置为厂商限制的80%，留出安全余量
    
    OPENAI_RPM_LIMIT: int = Field(
        3500,
        description="OpenAI API 速率限制（每分钟请求数）。免费用户通常为60 RPM，付费用户可达3500+ RPM"
    )
    
    ANTHROPIC_RPM_LIMIT: int = Field(
        3500,
        description="Anthropic API 速率限制（每分钟请求数）。Claude API 不同tier限制不同，建议保守设置"
    )
    
    DEEPSEEK_RPM_LIMIT: int = Field(
        3500,
        description="DeepSeek API 速率限制（每分钟请求数）"
    )
    
    # 注意：TAVILY_RATE_LIMIT_PER_MINUTE 已在上面定义，不重复

    # ==================== Gemini 网关配置 ====================
    GEMINI_API_KEY: str | None = Field(
        None,
        description="Gemini API 密钥（通过 OpenAI 兼容网关调用时使用）"
    )
    GEMINI_MODEL: str = Field(
        "google/gemini-3-flash-preview",
        description="Gemini 模型名称（OpenAI 兼容格式）"
    )
    GEMINI_BASE_URL: str | None = Field(
        None,
        description="Gemini 网关地址；若使用 OfoxAI 的 /gemini 入口，会自动转换为 /v1"
    )

    @property
    def get_gemini_openai_base_url(self) -> str | None:
        """
        获取适用于 OpenAI SDK 的 Gemini 兼容 Base URL

        说明：
        - 当前项目通过 `AsyncOpenAI` 统一调用不同网关
        - OfoxAI 首页给出的 OpenAI 兼容入口是 `https://api.ofox.ai/v1`
        - 如果环境变量误配为 `https://api.ofox.ai/gemini`，这里自动纠正，避免 404

        Returns:
            适用于 OpenAI SDK 的 Base URL；未配置时返回 None
        """
        if not self.GEMINI_BASE_URL:
            return None

        normalized_url = self.GEMINI_BASE_URL.rstrip("/")
        if normalized_url.endswith("/gemini"):
            return normalized_url[: -len("/gemini")] + "/v1"
        return normalized_url
    
    # ==================== LLM 配置 ====================
    # A1: Intent Analyzer (需求分析师)
    ANALYZER_PROVIDER: str = Field("openai", description="模型提供商")
    ANALYZER_MODEL: str = Field("gpt-4o-mini", description="模型名称")
    ANALYZER_BASE_URL: str | None = Field(None, description="自定义 API 端点")
    ANALYZER_API_KEY: str = Field("your_openai_api_key_here", description="API 密钥")
    
    # A2: Curriculum Architect (课程架构师)
    ARCHITECT_PROVIDER: str = Field("anthropic", description="模型提供商")
    ARCHITECT_MODEL: str = Field("claude-3-5-sonnet-20241022", description="模型名称")
    ARCHITECT_BASE_URL: str | None = None
    ARCHITECT_API_KEY: str = Field("your_anthropic_api_key_here", description="API 密钥")
    
    # A3: Structure Validator (结构审查员)
    VALIDATOR_PROVIDER: str = Field("openai", description="模型提供商")
    VALIDATOR_MODEL: str = Field("gpt-4o-mini", description="模型名称")
    VALIDATOR_BASE_URL: str | None = None
    VALIDATOR_API_KEY: str = Field("your_openai_api_key_here", description="API 密钥")
    
    # A2E: Roadmap Editor (路线图编辑师)
    EDITOR_PROVIDER: str = Field("anthropic", description="模型提供商")
    EDITOR_MODEL: str = Field("claude-3-5-sonnet-20241022", description="模型名称")
    EDITOR_BASE_URL: str | None = None
    EDITOR_API_KEY: str = Field("your_anthropic_api_key_here", description="API 密钥")
    
    # A4: Tutorial Generator (教程生成器)
    GENERATOR_PROVIDER: str = Field("anthropic", description="模型提供商")
    GENERATOR_MODEL: str = Field("claude-3-5-sonnet-20241022", description="模型名称")
    GENERATOR_BASE_URL: str | None = None
    GENERATOR_API_KEY: str = Field("your_anthropic_api_key_here", description="API 密钥")
    
    # A5: Resource Recommender (资源推荐师)
    RECOMMENDER_PROVIDER: str = Field("openai", description="模型提供商")
    RECOMMENDER_MODEL: str = Field("gpt-4o-mini", description="模型名称")
    RECOMMENDER_BASE_URL: str | None = None
    RECOMMENDER_API_KEY: str = Field("your_openai_api_key_here", description="API 密钥")
    
    # A6: Quiz Generator (测验生成器)
    QUIZ_PROVIDER: str = Field("openai", description="模型提供商")
    QUIZ_MODEL: str = Field("gpt-4o-mini", description="模型名称")
    QUIZ_BASE_URL: str | None = None
    QUIZ_API_KEY: str = Field("your_openai_api_key_here", description="API 密钥")

    # Mentor Agent（AI 伴学助手）
    MENTOR_AGENT_PROVIDER: str = Field("openai", description="AI 伴学助手模型提供商")
    MENTOR_AGENT_MODEL: str = Field("gpt-4o-mini", description="AI 伴学助手默认模型名称")
    MENTOR_AGENT_BASE_URL: str | None = Field(None, description="AI 伴学助手自定义 API 端点")
    MENTOR_AGENT_API_KEY: str | None = Field(None, description="AI 伴学助手 API 密钥")
    MENTOR_AGENT_TEMPERATURE: float = Field(0.7, description="AI 伴学助手采样温度")
    MENTOR_AGENT_MAX_TOKENS: int = Field(2048, description="AI 伴学助手最大输出 Token 数")

    @property
    def get_mentor_agent_api_key(self) -> str:
        """
        获取 AI 伴学助手 API 密钥

        优先使用专用配置；若未配置则回退到 ANALYZER_API_KEY，
        这样本地开发环境即使未单独配置也可以先跑通主链路。
        """
        return self.MENTOR_AGENT_API_KEY or self.ANALYZER_API_KEY
    
    # ==================== Modifier Agents 配置（内容修改）====================
    # 测验修改师（Quiz Modifier）
    QUIZ_MODIFIER_PROVIDER: str = Field("openai", description="模型提供商")
    QUIZ_MODIFIER_MODEL: str = Field("gpt-4o-mini", description="模型名称")
    QUIZ_MODIFIER_BASE_URL: str | None = None
    QUIZ_MODIFIER_API_KEY: str | None = Field(
        None, description="API 密钥（默认复用 QUIZ_API_KEY）"
    )
    
    @property
    def get_quiz_modifier_api_key(self) -> str:
        """获取测验修改师 API 密钥（优先使用专用配置，否则复用 QUIZ）"""
        return self.QUIZ_MODIFIER_API_KEY or self.QUIZ_API_KEY
    
    # ==================== Redis 配置 ====================
    # 优先使用 REDIS_URL（支持 Upstash 等云服务提供的完整连接字符串）
    REDIS_URL_ENV: str | None = Field(
        None,
        alias="REDIS_URL",
        description="Redis 完整连接 URL（优先，支持 redis:// 和 rediss://）"
    )
    REDIS_HOST: str = Field("localhost", description="Redis 主机（当 REDIS_URL 未设置时使用）")
    REDIS_PORT: int = Field(6379, description="Redis 端口（当 REDIS_URL 未设置时使用）")
    REDIS_PASSWORD: str | None = Field(None, description="Redis 密码（可选，当 REDIS_URL 未设置时使用）")
    REDIS_DB: int = Field(0, description="Redis 数据库编号（当 REDIS_URL 未设置时使用）")
    
    @property
    def get_redis_url(self) -> str:
        """
        获取 Redis 连接 URL
        
        优先级：
        1. REDIS_URL 环境变量（直接使用，支持 Upstash 等云服务的完整 URL）
        2. 根据 REDIS_HOST、REDIS_PORT 等配置构建
        
        Returns:
            Redis 连接 URL（支持 redis:// 和 rediss:// 协议）
        """
        # 如果提供了完整的 REDIS_URL，直接使用（适用于 Upstash 等云服务）
        if self.REDIS_URL_ENV:
            return self.REDIS_URL_ENV
        
        # 否则根据传统配置构建 URL
        if self.REDIS_PASSWORD:
            return f"redis://default:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    @property
    def REDIS_URL(self) -> str:
        """
        获取 Redis 连接 URL
        """
        return self.get_redis_url

    # ==================== Mentor 运行时配置 ====================
    MENTOR_STM_WINDOW_SIZE: int = Field(
        20,
        description="AI 伴学助手短期记忆窗口大小（按消息条数）"
    )
    MENTOR_STM_TTL_SECONDS: int = Field(
        86400,
        description="AI 伴学助手短期记忆 TTL（秒）"
    )
    MENTOR_LTM_TOP_K: int = Field(
        5,
        description="AI 伴学助手长期记忆召回数量"
    )
    MENTOR_MAX_MESSAGE_LENGTH: int = Field(
        4000,
        description="单条用户消息最大长度"
    )
    MENTOR_CONTEXT_EXCERPT_MAX_LENGTH: int = Field(
        1200,
        description="章节上下文截断长度"
    )
    MENTOR_RATE_LIMIT_PER_MINUTE: int = Field(
        30,
        description="单用户每分钟请求上限"
    )
    MENTOR_IP_RATE_LIMIT_PER_MINUTE: int = Field(
        60,
        description="单 IP 每分钟请求上限"
    )
    MENTOR_TASK_DONE_TTL_SECONDS: int = Field(
        604800,
        description="异步任务幂等完成标记 TTL（秒）"
    )
    MENTOR_MEMORY_LOCK_TIMEOUT_SECONDS: int = Field(
        30,
        description="长期记忆提炼分布式锁超时时间（秒）"
    )
    MENTOR_MEMORY_LOCK_RETRY_SECONDS: float = Field(
        0.2,
        description="长期记忆提炼锁重试间隔（秒）"
    )
    MENTOR_REFLECTION_MIN_MESSAGES: int = Field(
        50,
        description="触发长对话 reflection 的最小消息数"
    )
    MENTOR_LTM_CACHE_TTL_SECONDS: int = Field(
        600,
        description="AI 伴学助手长期记忆预热缓存 TTL（秒，默认 10 分钟）"
    )
    MENTOR_CONTEXT_CACHE_TTL_SECONDS: int = Field(
        1800,
        description="AI 伴学助手学习上下文预热缓存 TTL（秒，默认 30 分钟）"
    )

    # ==================== Mem0 配置 ====================
    MEM0_ENABLED: bool = Field(
        False,
        description="是否启用 Mem0 长期记忆能力"
    )
    MEM0_CONFIG_JSON: str | None = Field(
        None,
        description="Mem0 配置 JSON 字符串；生产环境可通过此字段注入 PgVector 配置"
    )
    MEM0_LTM_COLLECTION_NAME: str = Field(
        "mentor_memories",
        description="Mem0 长期记忆集合名称"
    )

    @property
    def get_mem0_config_json(self) -> str | None:
        """
        获取 Mem0 配置 JSON

        读取优先级：
        1. `MEM0_CONFIG_JSON` 为 JSON 字符串时直接使用。
        2. `MEM0_CONFIG_JSON` 为文件路径时读取对应文件。
        3. 回退读取后端根目录下的 `mem0_config.json`。
        """
        raw_value = (self.MEM0_CONFIG_JSON or "").strip()
        if raw_value:
            if raw_value.startswith("{"):
                return raw_value

            candidate_path = Path(raw_value)
            if not candidate_path.is_absolute():
                candidate_path = self._backend_dir / candidate_path
            if candidate_path.exists():
                return candidate_path.read_text(encoding="utf-8")

        default_config_path = self._backend_dir / "mem0_config.json"
        if default_config_path.exists():
            return default_config_path.read_text(encoding="utf-8")

        return None
    
    @property
    def get_tavily_api_keys(self) -> list[str]:
        """
        解析并返回所有可用的 Tavily API Keys
        
        优先级: TAVILY_API_KEY_LIST → TAVILY_API_KEY
        
        Returns:
            有效的 API Key 列表（已过滤无效值）
        """
        import json
        
        keys = []
        
        # 方式 1: 从 TAVILY_API_KEY_LIST 解析（优先）
        if self.TAVILY_API_KEY_LIST:
            # 尝试作为 JSON 数组解析
            try:
                keys = json.loads(self.TAVILY_API_KEY_LIST)
            except (json.JSONDecodeError, TypeError):
                # 作为逗号分隔字符串解析
                keys = [k.strip() for k in self.TAVILY_API_KEY_LIST.split(',') if k.strip()]
        
        # 方式 2: 回退到单个 TAVILY_API_KEY
        if not keys and self.TAVILY_API_KEY:
            keys = [self.TAVILY_API_KEY]
        
        # 过滤无效 Key
        valid_keys = [k for k in keys if k and k != "your_tavily_api_key_here"]
        
        return valid_keys
    
    # ==================== 外部服务配置 ====================
    # 注意: Tavily 配置已移至 "Web Search 配置" 部分
    
    # ==================== 观测性配置 ====================
    OTEL_ENABLED: bool = Field(False, description="是否启用 OpenTelemetry")
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = Field(None, description="OTLP 导出端点")
    
    # ==================== 业务配置 ====================
    MAX_FRAMEWORK_RETRY: int = Field(3, description="路线图结构验证最大重试次数")
    HUMAN_REVIEW_TIMEOUT_HOURS: int = Field(24, description="人工审核超时时间（小时）")
    NOTIFICATION_PROGRESS_PUBLISH_TIMEOUT_SECONDS: float = Field(
        3.0,
        description="普通 progress 通知发布超时时间（秒）",
    )
    # PARALLEL_TUTORIAL_LIMIT 已废弃：改用 Celery --concurrency 参数控制全局并发
    # PARALLEL_TUTORIAL_LIMIT: int = Field(5, description="并发生成教程的最大数量")
    
    # 流式教程生成配置
    TUTORIAL_STREAM_BATCH_SIZE: int = Field(1, description="流式教程生成每批次并发数量（建议设置为1避免MinIO超时）")
    
    # 测试模式配置
    TEST_MODE_TRUNCATE_FRAMEWORK: bool = Field(
        False,
        description="测试模式：在content_generation阶段前截断Framework，只保留第一个Stage的第一个Module的所有Concept"
    )
    
    # 内容生成缓存配置
    CONTENT_GEN_CACHE_ENABLED: bool = Field(
        True,
        description="是否启用内容生成数据缓存（Redis）"
    )
    CONTENT_GEN_CACHE_TTL: int = Field(
        86400,
        description="内容生成缓存过期时间（秒，默认24小时）"
    )

    # ==================== 工作流控制配置 ====================
    # 核心 Agent（不可跳过）：Intent Analyzer、Curriculum Architect、Structure Validator、Content Generators
    # 可选 Agent（可通过环境变量跳过）：Human Review
    SKIP_HUMAN_REVIEW: bool = Field(
        False,
        description="跳过人工审核节点（Human Review）"
    )
    
    # ==================== 任务恢复配置 ====================
    ENABLE_TASK_RECOVERY: bool = Field(
        True,
        description="启用服务器重启后自动恢复被中断的任务"
    )
    TASK_RECOVERY_MAX_AGE_HOURS: int = Field(
        24,
        description="任务恢复最大年龄（小时），超过此时间的任务不会被恢复"
    )
    TASK_RECOVERY_MAX_CONCURRENT: int = Field(
        3,
        description="任务恢复最大并发数量"
    )
    TASK_RECOVERY_DELAY_SECONDS: float = Field(
        5.0,
        description="任务恢复之间的延迟（秒），避免瞬间压力"
    )
    
    # Pending 任务重新入队配置（队列清空后孤儿任务恢复）
    ENABLE_PENDING_TASK_RECOVERY: bool = Field(
        True,
        description="启用 pending 任务自动重新入队（队列清空/Worker 重启后）"
    )
    PENDING_TASK_RECOVERY_MAX_AGE_HOURS: int = Field(
        2,
        description="Pending 任务重新入队最大年龄（小时），仅处理此时间内创建的任务"
    )
    ENABLE_STALE_PENDING_TASK_CLEANUP: bool = Field(
        True,
        description="启用长期 pending 创建任务自动清理，避免历史孤儿任务污染排队统计"
    )
    STALE_PENDING_TASK_CLEANUP_AFTER_HOURS: int = Field(
        6,
        description="Pending 创建任务超过此小时数仍停留在 init 时，视为陈旧孤儿任务"
    )

    # Stale processing 任务清理配置（管理员手动清理 + 后台 watchdog）
    ENABLE_STALE_TASK_WATCHDOG: bool = Field(
        True,
        description="启用后台 watchdog，定期清理长期卡住的 processing 任务"
    )
    STALE_TASK_CLEANUP_AFTER_MINUTES: int = Field(
        30,
        description="任务超过此分钟数未更新时，视为卡住候选任务"
    )
    STALE_TASK_WATCHDOG_INTERVAL_SECONDS: int = Field(
        300,
        description="后台 watchdog 扫描间隔（秒）"
    )
    STALE_TASK_WATCHDOG_BATCH_SIZE: int = Field(
        20,
        description="后台 watchdog 单次最多处理的任务数量"
    )
    
    # ==================== JWT 认证配置 ====================
    JWT_SECRET_KEY: str = Field(
        "your-super-secret-jwt-key-change-in-production",
        description="JWT 签名密钥（生产环境必须修改）"
    )
    JWT_ALGORITHM: str = Field("HS256", description="JWT 加密算法")
    JWT_LIFETIME_SECONDS: int = Field(
        86400,  # 24 小时
        description="JWT 令牌有效期（秒）"
    )
    
    # ==================== 邮件服务配置（Resend）====================
    RESEND_API_KEY: str | None = Field(
        None,
        description="Resend API 密钥（用于发送邀请邮件）"
    )
    RESEND_FROM_EMAIL: str = Field(
        "noreply@fastlearning.app",
        description="发件人邮箱地址"
    )
    
    # 前端 URL（用于邮件中的链接）
    FRONTEND_URL: str = Field(
        "http://localhost:3000",
        description="前端应用 URL"
    )
    
    # ==================== 错误日志文件配置（仅本地环境）====================
    ENABLE_ERROR_LOG_FILE: bool = Field(
        False,
        description="是否启用错误日志文件（建议仅在本地开发环境启用）"
    )
    ERROR_LOG_FILE_PATH: str = Field(
        "logs/err.log",
        description="错误日志文件路径"
    )
    ERROR_LOG_FILE_MAX_SIZE: int = Field(
        10 * 1024 * 1024,
        description="错误日志文件最大大小（字节），默认10MB"
    )


settings = Settings()
