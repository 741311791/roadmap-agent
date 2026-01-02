"""merge concept metadata and celery task id branches

Revision ID: 4642afc7b515
Revises: c7e9f8b1a2d3, c0f1e2d3a4b5
Create Date: 2026-01-02 00:12:49.483651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4642afc7b515'
down_revision: Union[str, None] = ('c7e9f8b1a2d3', 'c0f1e2d3a4b5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

