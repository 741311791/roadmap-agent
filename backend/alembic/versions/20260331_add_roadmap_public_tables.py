"""add roadmap public tables

Revision ID: 20260331_roadmap_public
Revises: 20260330_mentor_model_thinking
Create Date: 2026-03-31 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260331_roadmap_public"
down_revision: Union[str, None] = "20260330_mentor_model_thinking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移。"""
    op.create_table(
        "roadmap_milestones",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("linear_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("start_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=False), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_roadmap_milestones_linear_id",
        "roadmap_milestones",
        ["linear_id"],
        unique=True,
    )
    op.create_index(
        "idx_roadmap_milestones_status_sort",
        "roadmap_milestones",
        ["status", "sort_order"],
        unique=False,
    )

    op.create_table(
        "roadmap_features",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("linear_id", sa.String(length=64), nullable=False),
        sa.Column("milestone_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="planned"),
        sa.Column("demo_url", sa.String(length=512), nullable=True),
        sa.Column(
            "labels",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("linear_url", sa.String(length=512), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["milestone_id"], ["roadmap_milestones.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_roadmap_features_linear_id",
        "roadmap_features",
        ["linear_id"],
        unique=True,
    )
    op.create_index(
        "idx_roadmap_features_milestone_sort",
        "roadmap_features",
        ["milestone_id", "sort_order"],
        unique=False,
    )
    op.create_index(
        "idx_roadmap_features_status_sort",
        "roadmap_features",
        ["status", "sort_order"],
        unique=False,
    )

    op.create_table(
        "planning_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("submitter_email", sa.String(length=255), nullable=True),
        sa.Column("vote_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "idx_planning_items_status_vote",
        "planning_items",
        ["status", "vote_count"],
        unique=False,
    )

    op.create_table(
        "planning_votes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("planning_item_id", sa.Integer(), nullable=False),
        sa.Column("voter_fingerprint", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["planning_item_id"], ["planning_items.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "planning_item_id",
            "voter_fingerprint",
            name="uq_planning_votes_item_fingerprint",
        ),
    )
    op.create_index(
        "ix_planning_votes_planning_item_id",
        "planning_votes",
        ["planning_item_id"],
        unique=False,
    )
    op.create_index(
        "idx_planning_votes_item_created",
        "planning_votes",
        ["planning_item_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """回滚迁移。"""
    op.drop_index("idx_planning_votes_item_created", table_name="planning_votes")
    op.drop_index("ix_planning_votes_planning_item_id", table_name="planning_votes")
    op.drop_table("planning_votes")

    op.drop_index("idx_planning_items_status_vote", table_name="planning_items")
    op.drop_table("planning_items")

    op.drop_index("idx_roadmap_features_status_sort", table_name="roadmap_features")
    op.drop_index("idx_roadmap_features_milestone_sort", table_name="roadmap_features")
    op.drop_index("ix_roadmap_features_linear_id", table_name="roadmap_features")
    op.drop_table("roadmap_features")

    op.drop_index("idx_roadmap_milestones_status_sort", table_name="roadmap_milestones")
    op.drop_index("ix_roadmap_milestones_linear_id", table_name="roadmap_milestones")
    op.drop_table("roadmap_milestones")
