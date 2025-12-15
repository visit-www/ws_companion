"""add ai provenance fields to smart_helper_cards

Revision ID: 9c9e7f7e0d7f
Revises: 4716e28da927
Create Date: 2025-02-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9c9e7f7e0d7f'
down_revision: Union[str, None] = '4716e28da927'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('smart_helper_cards', sa.Column('source', sa.String(length=20), server_default='manual', nullable=False))
    op.add_column('smart_helper_cards', sa.Column('generated_for_token', sa.String(length=255), nullable=True))
    op.add_column('smart_helper_cards', sa.Column('generated_hash', sa.String(length=64), nullable=True))
    op.add_column('smart_helper_cards', sa.Column('expires_at', sa.DateTime(), nullable=True))

    op.create_index(op.f('ix_smart_helper_cards_source'), 'smart_helper_cards', ['source'], unique=False)
    op.create_index(op.f('ix_smart_helper_cards_generated_for_token'), 'smart_helper_cards', ['generated_for_token'], unique=False)
    op.create_index(op.f('ix_smart_helper_cards_generated_hash'), 'smart_helper_cards', ['generated_hash'], unique=False)

    # Clean up server default so ORM default takes over for new rows
    op.alter_column('smart_helper_cards', 'source', server_default=None)


def downgrade() -> None:
    op.drop_index(op.f('ix_smart_helper_cards_generated_hash'), table_name='smart_helper_cards')
    op.drop_index(op.f('ix_smart_helper_cards_generated_for_token'), table_name='smart_helper_cards')
    op.drop_index(op.f('ix_smart_helper_cards_source'), table_name='smart_helper_cards')

    op.drop_column('smart_helper_cards', 'expires_at')
    op.drop_column('smart_helper_cards', 'generated_hash')
    op.drop_column('smart_helper_cards', 'generated_for_token')
    op.drop_column('smart_helper_cards', 'source')
