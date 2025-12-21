"""Merge parallel migrations

Revision ID: 6bf7fc12530a
Revises: add_tech_capability_analysis, refactor_tech_assessments
Create Date: 2025-12-20 15:35:24.944597

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6bf7fc12530a'
down_revision: Union[str, None] = ('add_tech_capability_analysis', 'refactor_tech_assessments')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

