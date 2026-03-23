"""add mentor memory job table and chat metadata columns

Revision ID: 20260322_mentor_memory
Revises: 20260315_home_perf_idx
Create Date: 2026-03-22 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260322_mentor_memory"
down_revision: Union[str, None] = "20260315_home_perf_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移。"""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.add_column(
        "chat_sessions",
        sa.Column("agent_type", sa.String(length=32), nullable=False, server_default="tutoring"),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("model_id", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_chat_sessions_agent_type", "chat_sessions", ["agent_type"], unique=False)

    op.add_column(
        "chat_messages",
        sa.Column("agent_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("model_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("trace_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("token_usage_input", sa.Integer(), nullable=True),
    )
    op.add_column(
        "chat_messages",
        sa.Column("token_usage_output", sa.Integer(), nullable=True),
    )
    op.create_index("ix_chat_messages_agent_type", "chat_messages", ["agent_type"], unique=False)
    op.create_index("ix_chat_messages_trace_id", "chat_messages", ["trace_id"], unique=False)

    op.create_table(
        "mentor_memory_jobs",
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("celery_task_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index("ix_mentor_memory_jobs_user_id", "mentor_memory_jobs", ["user_id"], unique=False)
    op.create_index(
        "ix_mentor_memory_jobs_session_id",
        "mentor_memory_jobs",
        ["session_id"],
        unique=False,
    )
    op.create_index(
        "ix_mentor_memory_jobs_celery_task_id",
        "mentor_memory_jobs",
        ["celery_task_id"],
        unique=False,
    )
    op.create_index("ix_mentor_memory_jobs_status", "mentor_memory_jobs", ["status"], unique=False)
    op.create_index(
        "ix_mentor_memory_jobs_message_id_unique",
        "mentor_memory_jobs",
        ["message_id"],
        unique=True,
    )
    op.create_index(
        "ix_mentor_memory_jobs_user_status_created",
        "mentor_memory_jobs",
        ["user_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_mentor_memory_jobs_session_created",
        "mentor_memory_jobs",
        ["session_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """回滚迁移。"""
    op.drop_index("ix_mentor_memory_jobs_session_created", table_name="mentor_memory_jobs")
    op.drop_index("ix_mentor_memory_jobs_user_status_created", table_name="mentor_memory_jobs")
    op.drop_index("ix_mentor_memory_jobs_message_id_unique", table_name="mentor_memory_jobs")
    op.drop_index("ix_mentor_memory_jobs_status", table_name="mentor_memory_jobs")
    op.drop_index("ix_mentor_memory_jobs_celery_task_id", table_name="mentor_memory_jobs")
    op.drop_index("ix_mentor_memory_jobs_session_id", table_name="mentor_memory_jobs")
    op.drop_index("ix_mentor_memory_jobs_user_id", table_name="mentor_memory_jobs")
    op.drop_table("mentor_memory_jobs")

    op.drop_index("ix_chat_messages_trace_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_agent_type", table_name="chat_messages")
    op.drop_column("chat_messages", "token_usage_output")
    op.drop_column("chat_messages", "token_usage_input")
    op.drop_column("chat_messages", "trace_id")
    op.drop_column("chat_messages", "model_id")
    op.drop_column("chat_messages", "agent_type")

    op.drop_index("ix_chat_sessions_agent_type", table_name="chat_sessions")
    op.drop_column("chat_sessions", "model_id")
    op.drop_column("chat_sessions", "agent_type")
