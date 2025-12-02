"""Add failed_concepts and execution_summary fields to roadmap_tasks

Revision ID: add_task_execution_fields
Revises: add_user_profile_table
Create Date: 2024-12-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'add_task_execution_fields'
down_revision: Union[str, None] = 'add_user_profile'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add failed_concepts and execution_summary columns to roadmap_tasks"""
    # Add failed_concepts column (JSON)
    op.add_column(
        'roadmap_tasks',
        sa.Column('failed_concepts', sa.JSON(), nullable=True)
    )
    
    # Add execution_summary column (JSON)
    op.add_column(
        'roadmap_tasks',
        sa.Column('execution_summary', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    """Remove failed_concepts and execution_summary columns"""
    op.drop_column('roadmap_tasks', 'execution_summary')
    op.drop_column('roadmap_tasks', 'failed_concepts')

