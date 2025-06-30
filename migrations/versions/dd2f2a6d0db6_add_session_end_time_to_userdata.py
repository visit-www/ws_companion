"""Add session_end_time to UserData

Revision ID: dd2f2a6d0db6
Revises: 102b29dc0450
Create Date: 2025-06-29 22:33:16.418800

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd2f2a6d0db6'
down_revision: Union[str, None] = '102b29dc0450'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('user_data', sa.Column('session_end_time', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('user_data', 'session_end_time')
