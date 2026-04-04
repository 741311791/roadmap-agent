"""add user feedbacks table

Revision ID: 20260331_user_feedbacks
Revises: 20260330_mentor_model_thinking
Create Date: 2026-03-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260331_user_feedbacks"
down_revision: Union[str, None] = "20260330_mentor_model_thinking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移。"""
    op.create_table(
        "user_feedbacks",
        sa.Column("feedback_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("username_snapshot", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("email_snapshot", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("summary", sa.String(length=200), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.Column("page_url", sa.String(length=2000), nullable=False),
        sa.Column("context_type", sa.String(length=64), nullable=False),
        sa.Column("roadmap_id", sa.String(length=255), nullable=True),
        sa.Column("concept_id", sa.String(length=255), nullable=True),
        sa.Column("task_id", sa.String(length=255), nullable=True),
        sa.Column("screenshot_filename", sa.String(length=255), nullable=True),
        sa.Column("screenshot_asset_url", sa.String(length=2000), nullable=True),
        sa.Column("submission_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("linear_issue_id", sa.String(length=64), nullable=True),
        sa.Column("linear_issue_identifier", sa.String(length=64), nullable=True),
        sa.Column("linear_issue_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("feedback_id"),
    )
    op.create_index(
        "idx_user_feedbacks_user_created_at",
        "user_feedbacks",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "idx_user_feedbacks_status_created_at",
        "user_feedbacks",
        ["submission_status", "created_at"],
        unique=False,
    )
    op.create_index("ix_user_feedbacks_user_id", "user_feedbacks", ["user_id"], unique=False)
    op.create_index("ix_user_feedbacks_roadmap_id", "user_feedbacks", ["roadmap_id"], unique=False)
    op.create_index("ix_user_feedbacks_concept_id", "user_feedbacks", ["concept_id"], unique=False)
    op.create_index("ix_user_feedbacks_task_id", "user_feedbacks", ["task_id"], unique=False)


def downgrade() -> None:
    """回滚迁移。"""
    op.drop_index("ix_user_feedbacks_task_id", table_name="user_feedbacks")
    op.drop_index("ix_user_feedbacks_concept_id", table_name="user_feedbacks")
    op.drop_index("ix_user_feedbacks_roadmap_id", table_name="user_feedbacks")
    op.drop_index("ix_user_feedbacks_user_id", table_name="user_feedbacks")
    op.drop_index("idx_user_feedbacks_status_created_at", table_name="user_feedbacks")
    op.drop_index("idx_user_feedbacks_user_created_at", table_name="user_feedbacks")
    op.drop_table("user_feedbacks")
