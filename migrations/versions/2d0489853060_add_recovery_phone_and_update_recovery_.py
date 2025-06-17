"""Add recovery_phone and update recovery_email

Revision ID: 2d0489853060
Revises: ad1ccbd32faa
Create Date: 2024-09-28 23:23:49.929058

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d0489853060'
down_revision: Union[str, None] = 'ad1ccbd32faa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Both columns already exist — no changes needed
    pass

def downgrade() -> None:
    # Remove the recovery_phone column during downgrade
    op.drop_column('users', 'recovery_phone')

    # Remove or downgrade the recovery_email column
    op.drop_column('users', 'recovery_email')
