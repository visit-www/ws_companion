"""Add cascading delete and update to all foreign keys

Revision ID: 6b1518eed307
Revises: 668517695bd5
Create Date: 2024-09-15 15:39:52.552382

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6b1518eed307'
down_revision = '668517695bd5'
branch_labels = None
depends_on = None


def upgrade():
    # Use recreate='always' to handle unnamed constraints in SQLite

    # Upgrade for 'references' table
    with op.batch_alter_table('references', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_references_content_id', 'contents', ['content_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    # Upgrade for 'user_content_states' table
    with op.batch_alter_table('user_content_states', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_content_states_user_id', 'users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key('fk_user_content_states_content_id', 'contents', ['content_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    # Upgrade for 'user_data' table
    with op.batch_alter_table('user_data', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_data_user_id', 'users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key('fk_user_data_content_id', 'contents', ['content_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    # Upgrade for 'user_feedbacks' table
    with op.batch_alter_table('user_feedbacks', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_feedbacks_user_id', 'users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')
        batch_op.create_foreign_key('fk_user_feedbacks_content_id', 'contents', ['content_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    # Upgrade for 'user_profiles' table
    with op.batch_alter_table('user_profiles', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_profiles_user_id', 'users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')

    # Upgrade for 'user_report_templates' table
    with op.batch_alter_table('user_report_templates', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_report_templates_user_id', 'users', ['user_id'], ['id'], onupdate='CASCADE', ondelete='CASCADE')


def downgrade():
    # Downgrade for 'user_report_templates' table
    with op.batch_alter_table('user_report_templates', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_report_templates_user_id', 'users', ['user_id'], ['id'])

    # Downgrade for 'user_profiles' table
    with op.batch_alter_table('user_profiles', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_profiles_user_id', 'users', ['user_id'], ['id'])

    # Downgrade for 'user_feedbacks' table
    with op.batch_alter_table('user_feedbacks', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_feedbacks_content_id', 'contents', ['content_id'], ['id'])
        batch_op.create_foreign_key('fk_user_feedbacks_user_id', 'users', ['user_id'], ['id'])

    # Downgrade for 'user_data' table
    with op.batch_alter_table('user_data', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_data_user_id', 'users', ['user_id'], ['id'], ondelete='CASCADE')
        batch_op.create_foreign_key('fk_user_data_content_id', 'contents', ['content_id'], ['id'], ondelete='CASCADE')

    # Downgrade for 'user_content_states' table
    with op.batch_alter_table('user_content_states', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_user_content_states_content_id', 'contents', ['content_id'], ['id'])
        batch_op.create_foreign_key('fk_user_content_states_user_id', 'users', ['user_id'], ['id'])

    # Downgrade for 'references' table
    with op.batch_alter_table('references', recreate='always') as batch_op:
        batch_op.create_foreign_key('fk_references_content_id', 'contents', ['content_id'], ['id'])

    # ### end Alembic commands ###