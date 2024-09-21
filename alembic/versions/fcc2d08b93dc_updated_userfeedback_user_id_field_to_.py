"""Updated Userfeedback user_id field to ensure that whenever user is deleted, the UsrFedback is not orphaned but get parent frm AnnymousUser

Revision ID: fcc2d08b93dc
Revises: 0f4f4002ed81
Create Date: 2024-09-20 16:43:05.054165

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from config import ANONYMOUS_USER_ID


# revision identifiers, used by Alembic.
revision: str = 'fcc2d08b93dc'
down_revision: Union[str, None] = '0f4f4002ed81'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Ensure the anonymous user exists
    connection = op.get_bind()
    result = connection.execute(
        sa.text("SELECT id FROM users WHERE id = :id"),
        {'id': str(ANONYMOUS_USER_ID)}
    ).fetchone()

    if not result:
        # Insert the anonymous user if not present
        connection.execute(
            sa.text("""
                INSERT INTO users (id, username, password, email, is_paid, is_admin, status, created_at)
                VALUES (:id, :username, :password, :email, :is_paid, :is_admin, :status, :created_at)
            """),
            id=str(ANONYMOUS_USER_ID),
            username='anonymous',
            password='',  # Ensure this cannot be used to log in
            email='anonymous@example.com',
            is_paid=False,
            is_admin=False,
            status='active',
            created_at=datetime.utcnow()
        )

    # Set the default value for user_id column to anonymous user's ID
    op.alter_column(
        'user_feedbacks',
        'user_id',
        existing_type=UUID(as_uuid=True),
        nullable=False,
        server_default=f"{str(ANONYMOUS_USER_ID)}"
    )

    # Drop the existing foreign key constraint
    op.drop_constraint('user_feedbacks_user_id_fkey', 'user_feedbacks', type_='foreignkey')

    # Create a new foreign key constraint with ondelete='SET DEFAULT' and onupdate='CASCADE'
    op.create_foreign_key(
        'user_feedbacks_user_id_fkey',
        'user_feedbacks',
        'users',
        ['user_id'],
        ['id'],
        ondelete='SET DEFAULT',
        onupdate='CASCADE'
    )

def downgrade():
    # Reverse the changes made in upgrade()
    op.drop_constraint('user_feedbacks_user_id_fkey', 'user_feedbacks', type_='foreignkey')

    op.create_foreign_key(
        'user_feedbacks_user_id_fkey',
        'user_feedbacks',
        'users',
        ['user_id'],
        ['id']
    )

    op.alter_column(
        'user_feedbacks',
        'user_id',
        existing_type=UUID(as_uuid=True),
        nullable=False,
        server_default=None
    )

    # Optionally, delete the anonymous user (if appropriate)
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM users WHERE id = :id"),
        {'id': str(ANONYMOUS_USER_ID)}
    )