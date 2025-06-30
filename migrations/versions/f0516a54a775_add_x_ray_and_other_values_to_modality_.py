"""add x-ray and other values to modality_enum

Revision ID: f0516a54a775
Revises: dd2f2a6d0db6
Create Date: 2025-06-30 23:09:34.868339

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f0516a54a775'
down_revision: Union[str, None] = 'dd2f2a6d0db6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("ALTER TYPE modality_enum ADD VALUE IF NOT EXISTS 'x-ray';")
    op.execute("ALTER TYPE modality_enum ADD VALUE IF NOT EXISTS 'ct';")
    op.execute("ALTER TYPE modality_enum ADD VALUE IF NOT EXISTS 'mri';")
    op.execute("ALTER TYPE modality_enum ADD VALUE IF NOT EXISTS 'ultrasound';")
    op.execute("ALTER TYPE modality_enum ADD VALUE IF NOT EXISTS 'nuclear medicine';")
    op.execute("ALTER TYPE modality_enum ADD VALUE IF NOT EXISTS 'mammography';")
    op.execute("ALTER TYPE modality_enum ADD VALUE IF NOT EXISTS 'others';")

def downgrade():
    # ENUM values can't be removed easily in Postgres, so leave empty
    pass

