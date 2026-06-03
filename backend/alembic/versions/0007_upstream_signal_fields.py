"""upstream signal fields

Revision ID: 0007_upstream_signal_fields
Revises: 0006_opportunity_tenant_scope
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0007_upstream_signal_fields"
down_revision = "0006_opportunity_tenant_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("project_stage", sa.String(length=40), nullable=False, server_default="active_bid"))
    op.add_column("opportunities", sa.Column("signal_type", sa.String(length=80), nullable=True))
    op.add_column("opportunities", sa.Column("owner_type", sa.String(length=80), nullable=False, server_default="public_agency"))
    op.add_column("opportunities", sa.Column("forecast_rfp_date", sa.Date(), nullable=True))
    op.create_index(op.f("ix_opportunities_project_stage"), "opportunities", ["project_stage"], unique=False)
    op.create_index(op.f("ix_opportunities_signal_type"), "opportunities", ["signal_type"], unique=False)
    op.create_index(op.f("ix_opportunities_owner_type"), "opportunities", ["owner_type"], unique=False)
    op.create_index(op.f("ix_opportunities_forecast_rfp_date"), "opportunities", ["forecast_rfp_date"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_opportunities_forecast_rfp_date"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_owner_type"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_signal_type"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_project_stage"), table_name="opportunities")
    op.drop_column("opportunities", "forecast_rfp_date")
    op.drop_column("opportunities", "owner_type")
    op.drop_column("opportunities", "signal_type")
    op.drop_column("opportunities", "project_stage")
