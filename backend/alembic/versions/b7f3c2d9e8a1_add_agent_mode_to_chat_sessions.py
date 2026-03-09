"""add_agent_mode_to_chat_sessions

Revision ID: b7f3c2d9e8a1
Revises: a1b2c3d4e5f6
Create Date: 2026-03-08 23:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7f3c2d9e8a1"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为聊天会话增加 agent_mode 字段并建立索引。"""
    op.add_column(
        "chat_sessions",
        sa.Column(
            "agent_mode",
            sa.String(length=32),
            nullable=False,
            server_default="companion",
        ),
    )
    op.create_index(
        "ix_chat_sessions_user_roadmap_mode",
        "chat_sessions",
        ["user_id", "roadmap_id", "agent_mode"],
        unique=False,
    )


def downgrade() -> None:
    """回滚：删除 agent_mode 字段与相关索引。"""
    op.drop_index("ix_chat_sessions_user_roadmap_mode", table_name="chat_sessions")
    op.drop_column("chat_sessions", "agent_mode")
