"""add mentor model configs table

Revision ID: 20260329_mentor_models
Revises: 20260322_mentor_memory
Create Date: 2026-03-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260329_mentor_models"
down_revision: Union[str, None] = "20260322_mentor_memory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移。"""
    op.create_table(
        "mentor_model_configs",
        sa.Column("model_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default="openai"),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("supports_streaming", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "supports_structured_output",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("supports_tools", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("scope", sa.String(length=32), nullable=False, server_default="system"),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("test_status", sa.String(length=32), nullable=False, server_default="untested"),
        sa.Column("last_tested_at", sa.DateTime(), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("model_id"),
    )
    op.create_index(
        "idx_mentor_model_configs_scope_owner",
        "mentor_model_configs",
        ["scope", "owner_user_id"],
        unique=False,
    )
    op.create_index(
        "idx_mentor_model_configs_active_visible",
        "mentor_model_configs",
        ["is_active", "is_visible"],
        unique=False,
    )
    op.create_index(
        "ix_mentor_model_configs_scope",
        "mentor_model_configs",
        ["scope"],
        unique=False,
    )
    op.create_index(
        "ix_mentor_model_configs_owner_user_id",
        "mentor_model_configs",
        ["owner_user_id"],
        unique=False,
    )
    op.create_index(
        "uix_mentor_model_configs_system_default",
        "mentor_model_configs",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default = true AND scope = 'system'"),
    )


def downgrade() -> None:
    """回滚迁移。"""
    op.drop_index(
        "uix_mentor_model_configs_system_default",
        table_name="mentor_model_configs",
    )
    op.drop_index(
        "ix_mentor_model_configs_owner_user_id",
        table_name="mentor_model_configs",
    )
    op.drop_index("ix_mentor_model_configs_scope", table_name="mentor_model_configs")
    op.drop_index(
        "idx_mentor_model_configs_active_visible",
        table_name="mentor_model_configs",
    )
    op.drop_index(
        "idx_mentor_model_configs_scope_owner",
        table_name="mentor_model_configs",
    )
    op.drop_table("mentor_model_configs")

