"""add missing module_name enum values

Revision ID: 6ca3c6e6c628
Revises: b33312169f20
Create Date: 2025-11-27 18:10:49.417896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ca3c6e6c628'
down_revision: Union[str, None] = 'b33312169f20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
