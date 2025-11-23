"""add template section JSON fields

Revision ID: 13db3fc07d75
Revises: 5ba5dd3a8dae
Create Date: 2025-11-23 13:05:02.331121

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '13db3fc07d75'
down_revision: Union[str, None] = '5ba5dd3a8dae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add JSON fields for structured template sections."""
    # AdminReportTemplate: add definition_json
    op.add_column(
        "admin_report_templates",
        sa.Column("definition_json", sa.JSON(), nullable=True),
    )

    # UserReportTemplate: add section_values_json
    op.add_column(
        "user_report_templates",
        sa.Column("section_values_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Drop JSON fields for structured template sections."""
    # Drop in reverse order of creation
    op.drop_column("user_report_templates", "section_values_json")
    op.drop_column("admin_report_templates", "definition_json")
