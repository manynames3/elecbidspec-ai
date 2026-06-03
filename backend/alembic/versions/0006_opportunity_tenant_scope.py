"""opportunity tenant scope

Revision ID: 0006_opportunity_tenant_scope
Revises: 0005_saved_searches
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0006_opportunity_tenant_scope"
down_revision = "0005_saved_searches"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("tenant_id", sa.String(length=80), nullable=False, server_default="public"),
    )
    op.create_index(op.f("ix_opportunities_tenant_id"), "opportunities", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_opportunities_tenant_id"), table_name="opportunities")
    op.drop_column("opportunities", "tenant_id")
