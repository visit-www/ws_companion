"""Convert UserCPDState.id to UUID

Revision ID: 85714800c9bb
Revises: 23cfddf90b0e
Create Date: 2025-06-22

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import uuid

# revision identifiers, used by Alembic.
revision: str = '85714800c9bb'
down_revision: Union[str, None] = '23cfddf90b0e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop existing user_cpd_states table (make sure you're okay losing its data)
    op.drop_table('user_cpd_states')

    # Recreate with UUID as primary key
    op.create_table(
        'user_cpd_states',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('appraisal_cycle_start', sa.String(length=20), nullable=False),
        sa.Column('appraisal_cycle_end', sa.String(length=20), nullable=False),
        sa.Column('current_cpd_year_start', sa.String(length=20), nullable=False),
        sa.Column('current_cpd_year_end', sa.String(length=20), nullable=False),
        sa.Column('appraisal_cycle_start_date', sa.Date(), nullable=True),
        sa.Column('appraisal_cycle_end_date', sa.Date(), nullable=True),
        sa.Column('current_cpd_year_start_date', sa.Date(), nullable=True),
        sa.Column('current_cpd_year_end_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    # Add cpd_state_id to cpd_logs and create foreign key
    op.add_column('cpd_logs', sa.Column('cpd_state_id', sa.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        'fk_cpdlog_cpdstate',
        'cpd_logs',
        'user_cpd_states',
        ['cpd_state_id'],
        ['id']
    )


def downgrade() -> None:
    op.drop_constraint('fk_cpdlog_cpdstate', 'cpd_logs', type_='foreignkey')
    op.drop_column('cpd_logs', 'cpd_state_id')
    op.drop_table('user_cpd_states')