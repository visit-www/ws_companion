"""normalize enums to lowercase for body_part_enum, module_name, category_name

Revision ID: 7c653abfb3ca
Revises: f0516a54a775
Create Date: 2025-07-01 00:05:45.214720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7c653abfb3ca'
down_revision: Union[str, None] = 'f0516a54a775'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_contents_category;")
    op.execute("DROP INDEX IF EXISTS ix_user_report_templates_category;")
    op.execute("DROP INDEX IF EXISTS ix_references_category;")
    op.execute("DROP INDEX IF EXISTS ix_contents_module;")
    op.execute("DROP INDEX IF EXISTS ix_user_report_templates_module;")
    op.execute("DROP INDEX IF EXISTS ix_admin_report_templates_module;")
    op.execute("DROP INDEX IF EXISTS ix_references_module;")
    op.execute("DROP INDEX IF EXISTS ix_user_report_templates_body_part;")

    # Convert to TEXT
    op.execute('ALTER TABLE user_report_templates ALTER COLUMN body_part TYPE TEXT;')
    op.execute('ALTER TABLE admin_report_templates ALTER COLUMN body_part TYPE TEXT;')
    op.execute('ALTER TABLE user_report_templates ALTER COLUMN category TYPE TEXT;')
    op.execute('ALTER TABLE contents ALTER COLUMN category TYPE TEXT;')
    op.execute('ALTER TABLE "references" ALTER COLUMN category TYPE TEXT;')
    op.execute('ALTER TABLE user_report_templates ALTER COLUMN module TYPE TEXT;')
    op.execute('ALTER TABLE admin_report_templates ALTER COLUMN module TYPE TEXT;')
    op.execute('ALTER TABLE contents ALTER COLUMN module TYPE TEXT;')
    op.execute('ALTER TABLE "references" ALTER COLUMN module TYPE TEXT;')
    op.execute('ALTER TABLE user_data ALTER COLUMN subspecialty_tags TYPE TEXT[];')
    op.execute('ALTER TABLE user_profiles ALTER COLUMN preferred_subspecialties TYPE TEXT[];')

    # Drop old enums
    op.execute('DROP TYPE body_part_enum;')
    op.execute('DROP TYPE category_name;')
    op.execute('DROP TYPE module_name;')

    # Recreate enums
    op.execute("""
        CREATE TYPE body_part_enum AS ENUM (
            'neuro','head_and_neck','ent','pediatrics','msk','lung','cardiac',
            'endocrine','hepatobiliary','urology','gynaecology','upper_gi',
            'vascular','oncology','miscellaneous','breast','others'
        );
    """)
    op.execute("""
        CREATE TYPE category_name AS ENUM (
            'guidelines','classifications','differential_diagnosis','vetting_tools','anatomy',
            'curated_contents','report_checker','rad_calculators','tnm_staging','image_search',
            'physics','governance_audits','courses','research_tools','music','report_template'
        );
    """)
    op.execute("""
        CREATE TYPE module_name AS ENUM (
            'head_and_neck','neuroradiology','chest','cardiovascular','breast','gastrointestinal',
            'abdominal','genitourinary','musculoskeletal','vascular','pediatric','oncologic',
            'emergency','interventional','nuclear_medicine','radiographers','others'
        );
    """)

    # Normalize data
    op.execute("UPDATE user_report_templates SET body_part = LOWER(body_part), category = LOWER(category), module = LOWER(module);")
    op.execute("UPDATE admin_report_templates SET body_part = LOWER(body_part), module = LOWER(module);")
    op.execute("UPDATE contents SET category = LOWER(category), module = LOWER(module);")
    op.execute("UPDATE \"references\" SET category = LOWER(category), module = LOWER(module);")
    op.execute("UPDATE user_data SET subspecialty_tags = ARRAY(SELECT LOWER(unnest(subspecialty_tags)));")
    op.execute("UPDATE user_profiles SET preferred_subspecialties = ARRAY(SELECT LOWER(unnest(preferred_subspecialties)));")

    # Recast to enum
    op.execute("ALTER TABLE user_report_templates ALTER COLUMN body_part TYPE body_part_enum USING body_part::body_part_enum;")
    op.execute("ALTER TABLE admin_report_templates ALTER COLUMN body_part TYPE body_part_enum USING body_part::body_part_enum;")
    op.execute("ALTER TABLE user_report_templates ALTER COLUMN category TYPE category_name USING category::category_name;")
    op.execute("ALTER TABLE contents ALTER COLUMN category TYPE category_name USING category::category_name;")
    op.execute("ALTER TABLE \"references\" ALTER COLUMN category TYPE category_name USING category::category_name;")
    op.execute("ALTER TABLE user_report_templates ALTER COLUMN module TYPE module_name USING module::module_name;")
    op.execute("ALTER TABLE admin_report_templates ALTER COLUMN module TYPE module_name USING module::module_name;")
    op.execute("ALTER TABLE contents ALTER COLUMN module TYPE module_name USING module::module_name;")
    op.execute("ALTER TABLE \"references\" ALTER COLUMN module TYPE module_name USING module::module_name;")
    op.execute("ALTER TABLE user_data ALTER COLUMN subspecialty_tags TYPE module_name[] USING subspecialty_tags::module_name[];")
    op.execute("ALTER TABLE user_profiles ALTER COLUMN preferred_subspecialties TYPE module_name[] USING preferred_subspecialties::module_name[];")

    # Recreate indexes
    op.execute("CREATE INDEX ix_contents_category ON contents (category);")
    op.execute("CREATE INDEX ix_user_report_templates_category ON user_report_templates (category);")
    op.execute("CREATE INDEX ix_references_category ON \"references\" (category);")
    op.execute("CREATE INDEX ix_contents_module ON contents (module);")
    op.execute("CREATE INDEX ix_user_report_templates_module ON user_report_templates (module);")
    op.execute("CREATE INDEX ix_admin_report_templates_module ON admin_report_templates (module);")
    op.execute("CREATE INDEX ix_references_module ON \"references\" (module);")
    op.execute("CREATE INDEX ix_user_report_templates_body_part ON user_report_templates (body_part);")


def downgrade():
    raise NotImplementedError("Downgrade not supported for enum cleanup migration.")
