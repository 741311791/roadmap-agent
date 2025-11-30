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
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置"""
    
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
    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:3000"],
        description="允许的跨域来源"
    )
    
    # ==================== 数据库配置 ====================
    POSTGRES_HOST: str = Field("localhost", description="PostgreSQL 主机")
    POSTGRES_PORT: int = Field(5432, description="PostgreSQL 端口")
    POSTGRES_USER: str = Field("roadmap_user", description="数据库用户名")
    POSTGRES_PASSWORD: str = Field("roadmap_pass", description="数据库密码")
    POSTGRES_DB: str = Field("roadmap_db", description="数据库名称")
    
    @property
    def DATABASE_URL(self) -> str:
        """构建异步数据库连接 URL（用于 SQLAlchemy）"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    @property
    def CHECKPOINTER_DATABASE_URL(self) -> str:
        """构建 Checkpointer 数据库连接 URL（用于 AsyncPostgresSaver）"""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
    
    # ==================== S3/MinIO 配置 ====================
    S3_ENDPOINT_URL: str = Field("http://localhost:9000", description="S3 兼容端点（MinIO）")
    S3_ACCESS_KEY_ID: str = Field("minioadmin", description="访问密钥 ID")
    S3_SECRET_ACCESS_KEY: str = Field("minioadmin123", description="访问密钥")
    S3_BUCKET_NAME: str = Field("roadmap-content", description="存储桶名称")
    S3_REGION: str | None = Field(None, description="区域（MinIO 可留空）")
    
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
    
    # ==================== Redis 配置 ====================
    REDIS_HOST: str = Field("localhost", description="Redis 主机")
    REDIS_PORT: int = Field(6379, description="Redis 端口")
    REDIS_PASSWORD: str | None = Field(None, description="Redis 密码（可选）")
    REDIS_DB: int = Field(0, description="Redis 数据库编号")
    
    @property
    def REDIS_URL(self) -> str:
        """构建 Redis 连接 URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
    
    # ==================== 外部服务配置 ====================
    TAVILY_API_KEY: str = Field("your_tavily_api_key_here", description="Tavily API 密钥（用于 Web 搜索）")
    
    # ==================== 观测性配置 ====================
    OTEL_ENABLED: bool = Field(False, description="是否启用 OpenTelemetry")
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = Field(None, description="OTLP 导出端点")
    
    # ==================== 业务配置 ====================
    MAX_FRAMEWORK_RETRY: int = Field(3, description="路线图结构验证最大重试次数")
    HUMAN_REVIEW_TIMEOUT_HOURS: int = Field(24, description="人工审核超时时间（小时）")
    PARALLEL_TUTORIAL_LIMIT: int = Field(10, description="并发生成教程的最大数量（非流式模式）")
    
    # 流式教程生成配置
    TUTORIAL_STREAM_BATCH_SIZE: int = Field(1, description="流式教程生成每批次并发数量（建议设置为1避免MinIO超时）")

    # ==================== 工作流控制配置 ====================
    # 核心 Agent（不可跳过）：Intent Analyzer、Curriculum Architect、Tutorial Generator
    # 可选 Agent（可通过环境变量跳过）：
    SKIP_STRUCTURE_VALIDATION: bool = Field(
        False,
        description="跳过结构验证和路线图编辑（Structure Validator + Roadmap Editor）"
    )
    SKIP_HUMAN_REVIEW: bool = Field(
        False,
        description="跳过人工审核节点（Human Review）"
    )
    SKIP_TUTORIAL_GENERATION: bool = Field(
        False,
        description="跳过教程生成（仅生成路线图框架，不生成教程内容）"
    )
    SKIP_RESOURCE_RECOMMENDATION: bool = Field(
        False,
        description="跳过资源推荐（Resource Recommender）"
    )
    SKIP_QUIZ_GENERATION: bool = Field(
        False,
        description="跳过测验生成（Quiz Generator）"
    )


settings = Settings()
