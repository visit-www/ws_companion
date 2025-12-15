"""add ai quota fields to user

Revision ID: 0f5a7fb93577
Revises: 9c9e7f7e0d7f
Create Date: 2025-02-14 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0f5a7fb93577'
down_revision: Union[str, None] = '9c9e7f7e0d7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('ai_calls_used_today', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('ai_calls_last_reset', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('ai_daily_quota_override', sa.Integer(), nullable=True))
    op.alter_column('users', 'ai_calls_used_today', server_default=None)


def downgrade() -> None:
    op.drop_column('users', 'ai_daily_quota_override')
    op.drop_column('users', 'ai_calls_last_reset')
    op.drop_column('users', 'ai_calls_used_today')
