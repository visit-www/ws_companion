"""add source_detail to smart_helper_cards

Revision ID: 1d2b3c4d5e6f
Revises: 0f5a7fb93577
Create Date: 2025-02-14 01:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1d2b3c4d5e6f'
down_revision: Union[str, None] = '0f5a7fb93577'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('smart_helper_cards', sa.Column('source_detail', sa.String(length=50), nullable=True))
    op.create_index(op.f('ix_smart_helper_cards_source_detail'), 'smart_helper_cards', ['source_detail'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_smart_helper_cards_source_detail'), table_name='smart_helper_cards')
    op.drop_column('smart_helper_cards', 'source_detail')
