"""Add is_active field to UserCPDState

Revision ID: 23cfddf90b0e
Revises: 9e4719c3e6d7
Create Date: 2025-06-21 23:04:14.477963

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '23cfddf90b0e'
down_revision: Union[str, None] = '9e4719c3e6d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_cpd_states', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.execute("UPDATE user_cpd_states SET is_active = false")  # Set default for existing rows
    op.alter_column('user_cpd_states', 'is_active', nullable=False)


def downgrade() -> None:
    op.drop_column('user_cpd_states', 'is_active')
