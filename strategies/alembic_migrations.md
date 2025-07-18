### Complete Guide: Alembic Migration Setup and Troubleshooting

Here’s a structured guide with all the relevant files, steps, and troubleshooting details, based on what we did to get the migration working successfully.

---

### **Step-by-Step Process for Alembic Migration Setup**

#### **1. Initial Alembic Migration Script**

The following script was generated as your initial migration. It creates the necessary tables for your app, such as `users`, `contents`, `user_profiles`, and more.

**Migration Script**: `migrations/versions/4726a3538ac2_initial_migration.py`

```python
"""Initial migration

Revision ID: 4726a3538ac2
Revises: 
Create Date: 2024-09-22 15:57:05.188541
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4726a3538ac2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Table creation commands generated by Alembic.
    op.create_table('admin_report_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        # Other fields omitted for brevity...
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_report_templates_body_part'), 'admin_report_templates', ['body_part'], unique=False)
    # Similarly create other tables, contents, users, user_profiles...
    
def downgrade() -> None:
    # Table removal commands to downgrade migration.
    op.drop_table('admin_report_templates')
    # Similarly drop other tables...
```

---

#### **2. Alembic Configuration File**

Ensure your `alembic.ini` file is correctly set up. Here’s the configuration:

```ini
# alembic.ini

[alembic]
script_location = migrations  # Points to the 'migrations' folder

sqlalchemy.url = postgresql://admin:811976@localhost/wscdb

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[logger_alembic]
level = DEBUG
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic
```

---

#### **3. Alembic `env.py` Configuration**

Make sure `env.py` is properly set up to target your database and SQLAlchemy models. Below is the refined version we used:

```python
# migrations/env.py

import os
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.models import Base  # Make sure this is the correct import path for your models

config = context.config

# Fetch the database URL
database_url = os.getenv("DATABASE_URL", "postgresql://admin:811976@localhost/wscdb")

# Handle Heroku's old 'postgres://' URL format
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

config.set_main_option("sqlalchemy.url", database_url)

# Metadata from your models
target_metadata = Base.metadata

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

---

### **Troubleshooting Steps We Followed**

In case you encounter similar issues in the future, here’s a summary of the steps we took to resolve the migration not applying properly:

1. **Check Alembic Migration History**:
   - Run `alembic history` to see all applied migrations.
   - Run `alembic current` to check the current migration version.

2. **Manually Drop the `alembic_version` Table** (if stuck):
   - If the `alembic_version` table conflicts, drop it manually:
     ```sql
     DROP TABLE alembic_version;
     ```

3. **Downgrade and Re-apply the Migration**:
   - Run `alembic downgrade base` to reset the database.
   - Then, run `alembic upgrade head` to reapply the migration.

4. **Manual Testing with SQLAlchemy**:
   - If necessary, manually test SQLAlchemy’s connection and table creation using a simple script to ensure the database connection is valid.

---

### **Future Safeguarding**

To avoid similar issues in the future:

- **Backup Migration Scripts**: Keep a copy of your initial migration script and critical database configuration files (`env.py`, `alembic.ini`).
- **Track Steps**: Record any troubleshooting steps (like those above) to quickly resolve issues.

---

Feel free to copy, save, or use this structured guide as a reference for future database and migration tasks! Let me know if you need further assistance or clarification!
Here is the full `migrations/versions/4726a3538ac2_initial_migration.py` script with all the tables included. This will serve as the complete reference for future use.

### Complete Initial Migration Script

```python
"""Initial migration

Revision ID: 4726a3538ac2
Revises: 
Create Date: 2024-09-22 15:57:05.188541
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4726a3538ac2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Create admin_report_templates table ###
    op.create_table('admin_report_templates',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('template_name', sa.String(length=255), nullable=True),
    sa.Column('body_part', sa.Enum('NEURO', 'HEAD_AND_NECK', 'ENT', 'PEDIATRICS', 'MSK', 'LUNG', 'CARDIAC', 'ENDOCRINE', 'HEPATOBILIARY', 'UROLOGY', 'GYNAECOLOGY', 'UPPER_GI', 'VASCULAR', 'ONCOLOGY', 'MISCELLANEOUS', 'BREAST', 'OTHERS', name='body_part_enum'), nullable=True),
    sa.Column('modality', sa.Enum('CT', 'X_RAY', 'MRI', 'ULTRASOUND', 'NUCLEAR_MEDICINE', 'MAMMOGRAPHY', 'OTHERS', name='modality_enum'), nullable=True),
    sa.Column('file', sa.String(length=255), nullable=True),
    sa.Column('filepath', sa.String(length=255), nullable=True),
    sa.Column('tags', sa.Text(), nullable=True),
    sa.Column('category', sa.String(), nullable=True),
    sa.Column('module', sa.Enum('HEAD_AND_NECK', 'NEURORADIOLOGY', 'CHEST', 'CARDIOVASCULAR', 'BREAST', 'GASTROINTESTINAL', 'ABDOMINAL', 'GENITOURINARY', 'MUSCULOSKELETAL', 'VASCULAR', 'PEDIATRIC', 'ONCOLOGIC', 'EMERGENCY', 'INTERVENTIONAL', 'NUCLEAR_MEDICINE', 'RADIOGRAPHERS', 'OTHERS', name='module_name'), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_report_templates_body_part'), 'admin_report_templates', ['body_part'], unique=False)
    op.create_index(op.f('ix_admin_report_templates_category'), 'admin_report_templates', ['category'], unique=False)
    op.create_index(op.f('ix_admin_report_templates_modality'), 'admin_report_templates', ['modality'], unique=False)
    op.create_index(op.f('ix_admin_report_templates_module'), 'admin_report_templates', ['module'], unique=False)
    op.create_index(op.f('ix_admin_report_templates_template_name'), 'admin_report_templates', ['template_name'], unique=True)

    # ### Create contents table ###
    op.create_table('contents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=565), nullable=False),
    sa.Column('category', sa.Enum('GUIDELINES', 'CLASSIFICATIONS', 'DIFFERENTIAL_DIAGNOSIS', 'VETTING_TOOLS', 'ANATOMY', 'CURATED_CONTENTS', 'REPORT_CHECKER', 'RAD_CALCULATORS', 'TNM_STAGING', 'IMAGE_SEARCH', 'PHYSICS', 'GOVERNANCE_AUDITS', 'COURSES', 'RESEARCH_TOOLS', 'MUSIC', 'REPORT_TEMPLATE', name='category_name'), nullable=False),
    sa.Column('module', sa.Enum('HEAD_AND_NECK', 'NEURORADIOLOGY', 'CHEST', 'CARDIOVASCULAR', 'BREAST', 'GASTROINTESTINAL', 'ABDOMINAL', 'GENITOURINARY', 'MUSCULOSKELETAL', 'VASCULAR', 'PEDIATRIC', 'ONCOLOGIC', 'EMERGENCY', 'INTERVENTIONAL', 'NUCLEAR_MEDICINE', 'RADIOGRAPHERS', 'OTHERS', name='module_name'), nullable=False),
    sa.Column('status', sa.Enum('DRAFT', 'PUBLISHED', 'ARCHIVED', name='status'), nullable=True),
    sa.Column('file', sa.String(length=255), nullable=True),
    sa.Column('filepath', sa.String(length=255), nullable=True),
    sa.Column('external_url', sa.String(length=2083), nullable=True),
    sa.Column('embed_code', sa.Text(), nullable=True),
    sa.Column('keywords', sa.Text(), nullable=True),
    sa.Column('language', sa.String(length=20), nullable=True),
    sa.Column('content_tags', sa.Text(), nullable=True),
    sa.Column('importance_level', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='importance_level'), nullable=True),
    sa.Column('featured', sa.Boolean(), nullable=True),
    sa.Column('paid_access', sa.Boolean(), nullable=True),
    sa.Column('api_endpoint', sa.String(length=2083), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('version', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('last_accessed', sa.DateTime(), nullable=True),
    sa.Column('access_count', sa.Integer(), nullable=True),
    sa.Column('view_duration', sa.Integer(), nullable=True),
    sa.Column('created_by', sa.String(length=80), nullable=True),
    sa.Column('file_size', sa.Integer(), nullable=True),
    sa.Column('estimated_reading_time', sa.Integer(), nullable=True),
    sa.Column('bookmark_count', sa.Integer(), nullable=True),
    sa.Column('related_content', sa.Text(), nullable=True),
    sa.Column('related_api_links', sa.Text(), nullable=True),
    sa.Column('accessibility_features', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contents_category'), 'contents', ['category'], unique=False)
    op.create_index(op.f('ix_contents_content_tags'), 'contents', ['content_tags'], unique=False)
    op.create_index(op.f('ix_contents_file'), 'contents', ['file'], unique=False)
    op.create_index(op.f('ix_contents_filepath'), 'contents', ['filepath'], unique=False)
    op.create_index(op.f('ix_contents_id'), 'contents', ['id'], unique=False)
    op.create_index(op.f('ix_contents_keywords'), 'contents', ['keywords'], unique=False)
    op.create_index(op.f('ix_contents_module'), 'contents', ['module'], unique=False)
    op.create_index(op.f('ix_contents_title'), 'contents', ['title'], unique=False)

    # ### Create users table ###
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('username', sa.String(length=150), nullable=False),
    sa.Column('password', sa.String(length=250), nullable=False),
    sa.Column('email', sa.String(length=150), nullable=False),
    sa.Column('is_paid', sa.Boolean(), nullable=True),
    sa.Column('is_admin', sa.Boolean(), nullable=True),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # ### Create references table ###
    op.create_table('references',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('content_id', sa.Integer(), nullable=True),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('category', sa.Enum('GUIDELINES', 'CLASSIFICATIONS', 'DIFFERENTIAL_DIAGNOSIS', 'VETTING_TOOLS', 'ANATOMY', 'CURATED_CONTENTS', 'REPORT_CHECKER', 'RAD_CALCULATORS', 'TNM_STAGING', 'IMAGE_SEARCH', 'PHYSICS', 'GOVERNANCE_AUDITS', 'COURSES', 'RESEARCH_TOOLS', 'MUSIC', 'REPORT_TEMPLATE', name='category_name'), nullable=False),
    sa.Column('module', sa.Enum('HEAD_AND_NECK', 'NEURORADIOLOGY', 'CHEST', 'CARDIOVASCULAR', 'BREAST', 'GASTROINTESTINAL', 'ABDOMINAL', 'GENITOURINARY', 'MUSCULOSKELETAL', 'VASCULAR', 'PEDIATRIC', 'ONCOLOGIC', 'EMERGENCY', 'INTERVENTIONAL', 'NUCLEAR_MEDICINE', 'RADIOGRAPHERS', 'OTHERS', name='module_name'), nullable=False),
    sa.Column('file', sa.String(length=255), nullable=True),
    sa.Column('filepath', sa.String(length=255), nullable=True),
    sa.Column('url', sa.String(length=2083), nullable=True),
    sa.Column

('embed_code', sa.Text(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['content_id'], ['contents.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_references_category'), 'references', ['category'], unique=False)
    op.create_index(op.f('ix_references_file'), 'references', ['file'], unique=False)
    op.create_index(op.f('ix_references_module'), 'references', ['module'], unique=False)

    # ### Create user_content_states table ###
    op.create_table('user_content_states',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('content_id', sa.Integer(), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('modified_filepath', sa.String(length=255), nullable=True),
    sa.Column('annotations', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['content_id'], ['contents.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # ### Create user_data table ###
    op.create_table('user_data',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('content_id', sa.Integer(), nullable=True),
    sa.Column('interaction_type', sa.Enum('viewed', 'bookmarked', 'recommended', 'registered', 'logged_in', 'logged_out', 'updated_profile_pic', 'updated_username', 'updated_email', 'updated_report_templates', 'updated_category_module_preferences', 'updated_contents', 'added_feedback', name='interaction_types'), nullable=False),
    sa.Column('last_interaction', sa.DateTime(), nullable=False),
    sa.Column('feedback', sa.Text(), nullable=True),
    sa.Column('content_rating', sa.Integer(), nullable=True),
    sa.Column('time_spent', sa.Integer(), nullable=False),
    sa.Column('last_login', sa.DateTime(), nullable=True),
    sa.Column('current_login', sa.DateTime(), nullable=True),
    sa.Column('session_start_time', sa.DateTime(), nullable=True),
    sa.Column('login_count', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['content_id'], ['contents.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # ### Create user_feedbacks table ###
    op.create_table('user_feedbacks',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), server_default='123e4567-e89b-12d3-a456-426614174000', nullable=False),
    sa.Column('content_id', sa.Integer(), nullable=True),
    sa.Column('feedback', sa.Text(), nullable=True),
    sa.Column('is_public', sa.Boolean(), nullable=True),
    sa.Column('user_display_name', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['content_id'], ['contents.id'], onupdate='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate='CASCADE', ondelete='SET DEFAULT'),
    sa.PrimaryKeyConstraint('id')
    )

    # ### Create user_profiles table ###
    op.create_table('user_profiles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('profile_pic', sa.String(length=255), nullable=True),
    sa.Column('profile_pic_path', sa.String(length=255), nullable=True),
    sa.Column('preferred_categories', sa.Text(), nullable=True),
    sa.Column('preferred_modules', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # ### Create user_report_templates table ###
    op.create_table('user_report_templates',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('body_part', sa.Enum('NEURO', 'HEAD_AND_NECK', 'ENT', 'PEDIATRICS', 'MSK', 'LUNG', 'CARDIAC', 'ENDOCRINE', 'HEPATOBILIARY', 'UROLOGY', 'GYNAECOLOGY', 'UPPER_GI', 'VASCULAR', 'ONCOLOGY', 'MISCELLANEOUS', 'BREAST', 'OTHERS', name='body_part_enum'), nullable=True),
    sa.Column('modality', sa.Enum('CT', 'X_RAY', 'MRI', 'ULTRASOUND', 'NUCLEAR_MEDICINE', 'MAMMOGRAPHY', 'OTHERS', name='modality_enum'), nullable=True),
    sa.Column('template_name', sa.String(length=255), nullable=True),
    sa.Column('tags', sa.Text(), nullable=True),
    sa.Column('is_public', sa.Boolean(), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('category', sa.Enum('GUIDELINES', 'CLASSIFICATIONS', 'DIFFERENTIAL_DIAGNOSIS', 'VETTING_TOOLS', 'ANATOMY', 'CURATED_CONTENTS', 'REPORT_CHECKER', 'RAD_CALCULATORS', 'TNM_STAGING', 'IMAGE_SEARCH', 'PHYSICS', 'GOVERNANCE_AUDITS', 'COURSES', 'RESEARCH_TOOLS', 'MUSIC', 'REPORT_TEMPLATE', name='category_name'), nullable=True),
    sa.Column('module', sa.Enum('HEAD_AND_NECK', 'NEURORADIOLOGY', 'CHEST', 'CARDIOVASCULAR', 'BREAST', 'GASTROINTESTINAL', 'ABDOMINAL', 'GENITOURINARY', 'MUSCULOSKELETAL', 'VASCULAR', 'PEDIATRIC', 'ONCOLOGIC', 'EMERGENCY', 'INTERVENTIONAL', 'NUCLEAR_MEDICINE', 'RADIOGRAPHERS', 'OTHERS', name='module_name'), nullable=True),
    sa.Column('template_text', sa.Text(), nullable=True),
    sa.Column('file', sa.String(length=255), nullable=True),
    sa.Column('filepath', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_report_templates_body_part'), 'user_report_templates', ['body_part'], unique=False)
    op.create_index(op.f('ix_user_report_templates_category'), 'user_report_templates', ['category'], unique=False)
    op.create_index(op.f('ix_user_report_templates_is_public'), 'user_report_templates', ['is_public'], unique=False)
    op.create_index(op.f('ix_user_report_templates_modality'), 'user_report_templates', ['modality'], unique=False)
    op.create_index(op.f('ix_user_report_templates_module'), 'user_report_templates', ['module'], unique=False)
    op.create_index(op.f('ix_user_report_templates_template_name'), 'user_report_templates', ['template_name'], unique=True)
    op.create_index(op.f('ix_user_report_templates_user_id'), 'user_report_templates', ['user_id'], unique=False)


def downgrade() -> None:
    # Downgrade actions, drop the tables
    op.drop_index(op.f('ix_user_report_templates_user_id'), table_name='user_report_templates')
    op.drop_index(op.f('ix_user_report_templates_template_name'), table_name='user_report_templates')
    op.drop_index(op.f('ix_user_report_templates_module'), table_name='user_report_templates')
    op.drop_index(op.f('ix_user_report_templates_modality'), table_name='user_report_templates')
    op.drop_index(op.f('ix_user_report_templates_is_public'), table_name='user_report_templates')
    op.drop_index(op.f('ix_user_report_templates_category'), table_name='user_report_templates')
    op.drop_index(op.f('ix_user_report_templates_body_part'), table_name='user_report_templates')
    op.drop_table('user_report_templates')
    # Repeat for other tables...
    op.drop_table('user_profiles')
    op.drop_table('user_feedbacks')
    op.drop_table('user_data')
    op.drop_table('user_content_states')
    op.drop_table('references')
    op.drop_table('users')
    op.drop_table('contents')
    op.drop_table('admin_report_templates')
```

This is the full initial migration script containing all the tables and their respective fields. You can save this script for future reference or troubleshooting if needed.

Let me know if you need any more adjustments!
