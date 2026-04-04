"""add supports_thinking to mentor model configs

Revision ID: 20260330_mentor_model_thinking
Revises: 20260329_mentor_models
Create Date: 2026-03-30 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260330_mentor_model_thinking"
down_revision: Union[str, None] = "20260329_mentor_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移。"""
    op.add_column(
        "mentor_model_configs",
        sa.Column(
            "supports_thinking",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """回滚迁移。"""
    op.drop_column("mentor_model_configs", "supports_thinking")
