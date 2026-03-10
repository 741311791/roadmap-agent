"""add_model_name_to_chat_sessions

Revision ID: 9c2d7f4a1b33
Revises: b7f3c2d9e8a1
Create Date: 2026-03-10 00:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c2d7f4a1b33"
down_revision: Union[str, None] = "b7f3c2d9e8a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """为聊天会话增加 model_name 字段并建立复合索引。"""
    op.add_column(
        "chat_sessions",
        sa.Column(
            "model_name",
            sa.String(length=32),
            nullable=False,
            server_default="qwen-plus",  # pragma: allowlist secret
        ),
    )
    op.create_index(
        "ix_chat_sessions_user_roadmap_mode_model",
        "chat_sessions",
        ["user_id", "roadmap_id", "agent_mode", "model_name"],
        unique=False,
    )


def downgrade() -> None:
    """回滚：删除 model_name 字段与相关索引。"""
    op.drop_index("ix_chat_sessions_user_roadmap_mode_model", table_name="chat_sessions")
    op.drop_column("chat_sessions", "model_name")
