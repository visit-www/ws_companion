from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = 'ac6c59aa7a26'
down_revision = '9b0b556b716e'
branch_labels = None
depends_on = None


def upgrade():
    # Add last_updated to user table
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), nullable=False))

    # Add last_updated to guideline table
    with op.batch_alter_table('guideline', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_updated', sa.DateTime(), server_default=sa.func.now(), nullable=False))

    # Update existing rows with the current timestamp using SQLite-compatible syntax
    op.execute('UPDATE user SET last_updated = CURRENT_TIMESTAMP WHERE last_updated IS NULL')
    op.execute('UPDATE guideline SET last_updated = CURRENT_TIMESTAMP WHERE last_updated IS NULL')

    # Remove the server default if it's not desired for future inserts
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('last_updated', server_default=None)

    with op.batch_alter_table('guideline', schema=None) as batch_op:
        batch_op.alter_column('last_updated', server_default=None)


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('last_updated')

    with op.batch_alter_table('guideline', schema=None) as batch_op:
        batch_op.drop_column('last_updated')