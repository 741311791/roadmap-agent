"""
Alembic 环境配置
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import asyncio
from sqlalchemy.ext.asyncio import AsyncEngine

# 导入应用配置和模型
from app.config.settings import settings
from app.models.database import (
    Base,  # 重要：导入 Base，用于 User 表
    User, 
    RoadmapTask, 
    RoadmapMetadata, 
    TutorialMetadata,
    IntentAnalysisMetadata,
    ResourceRecommendationMetadata,
    QuizMetadata,
    TechStackAssessment,
    UserProfile,
    ExecutionLog,
    ConceptProgress,
    QuizAttempt,
    StructureValidationRecord,
    RoadmapEditRecord,
    ChatSession,
    ChatMessage,
    LearningNote,
    WaitlistEmail,
    TavilyAPIKey,
)
from sqlmodel import SQLModel
from sqlalchemy import MetaData

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 设置数据库 URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("+asyncpg", ""))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 关键修复：合并 Base.metadata 和 SQLModel.metadata
# User 表使用 Base (DeclarativeBase)
# 其他表使用 SQLModel
# 必须同时注册两个 metadata，否则 Alembic 会认为 User 表不存在
combined_metadata = MetaData()
for table in Base.metadata.tables.values():
    table.to_metadata(combined_metadata)
for table in SQLModel.metadata.tables.values():
    table.to_metadata(combined_metadata)

target_metadata = combined_metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # 忽略 LangGraph checkpoint 表
        include_object=lambda obj, name, type_, reflected, compare_to: (
            False if type_ == "table" and name in [
                "checkpoints", 
                "checkpoint_blobs", 
                "checkpoint_writes", 
                "checkpoint_migrations"
            ] else True
        )
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    # 配置 Alembic 忽略 LangGraph checkpoint 相关表
    # 这些表由 LangGraph 自动管理，不应该被 Alembic 迁移
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        include_schemas=True,
        # 忽略 LangGraph checkpoint 表
        include_object=lambda obj, name, type_, reflected, compare_to: (
            False if type_ == "table" and name in [
                "checkpoints", 
                "checkpoint_blobs", 
                "checkpoint_writes", 
                "checkpoint_migrations"
            ] else True
        )
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # 使用同步引擎进行迁移（Alembic 需要同步连接）
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg")
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = sync_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # 配置 Alembic 忽略 LangGraph checkpoint 相关表
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            include_schemas=True,
            # 忽略 LangGraph checkpoint 表
            include_object=lambda obj, name, type_, reflected, compare_to: (
                False if type_ == "table" and name in [
                    "checkpoints", 
                    "checkpoint_blobs", 
                    "checkpoint_writes", 
                    "checkpoint_migrations"
                ] else True
            )
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

