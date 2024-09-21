""" corrected spelling from loged_out to logged_out

Revision ID: a89bde3fdef8
Revises: fcc2d08b93dc
Create Date: 2024-09-21 00:53:01.651018

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a89bde3fdef8'
down_revision: Union[str, None] = 'fcc2d08b93dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Rename 'loged_out' to 'logged_out' in the existing enum type
    op.execute("ALTER TYPE interaction_types RENAME VALUE 'loged_out' TO 'logged_out'")

def downgrade():
    # Rename 'logged_out' back to 'loged_out'
    op.execute("ALTER TYPE interaction_types RENAME VALUE 'logged_out' TO 'loged_out'")
