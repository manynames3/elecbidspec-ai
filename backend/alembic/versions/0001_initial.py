"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=220), nullable=False),
        sa.Column("states_served", sa.JSON(), nullable=False),
        sa.Column("bonding_capacity", sa.Numeric(14, 2), nullable=True),
        sa.Column("cable_types_supplied", sa.JSON(), nullable=False),
        sa.Column("installation_capabilities", sa.JSON(), nullable=False),
        sa.Column("labor_type", sa.String(length=80), nullable=True),
        sa.Column("experience", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_company_profiles_id"), "company_profiles", ["id"], unique=False)

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("adapter", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingestion_jobs_adapter"), "ingestion_jobs", ["adapter"], unique=False)
    op.create_index(op.f("ix_ingestion_jobs_id"), "ingestion_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_ingestion_jobs_status"), "ingestion_jobs", ["status"], unique=False)

    op.create_table(
        "opportunities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=280), nullable=False),
        sa.Column("agency", sa.String(length=220), nullable=True),
        sa.Column("location", sa.String(length=220), nullable=True),
        sa.Column("state", sa.String(length=2), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("naics_code", sa.String(length=12), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("estimated_value", sa.Numeric(14, 2), nullable=True),
        sa.Column("attachments", sa.JSON(), nullable=False),
        sa.Column("extracted_specs", sa.JSON(), nullable=False),
        sa.Column("project_type", sa.String(length=80), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("classification_explanation", sa.Text(), nullable=True),
        sa.Column("fit_score", sa.Integer(), nullable=True),
        sa.Column("fit_explanation", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_opportunities_due_date"), "opportunities", ["due_date"], unique=False)
    op.create_index(op.f("ix_opportunities_fit_score"), "opportunities", ["fit_score"], unique=False)
    op.create_index(op.f("ix_opportunities_id"), "opportunities", ["id"], unique=False)
    op.create_index(op.f("ix_opportunities_project_type"), "opportunities", ["project_type"], unique=False)
    op.create_index(op.f("ix_opportunities_source"), "opportunities", ["source"], unique=False)
    op.create_index(op.f("ix_opportunities_state"), "opportunities", ["state"], unique=False)
    op.create_index(op.f("ix_opportunities_title"), "opportunities", ["title"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_opportunities_title"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_state"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_source"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_project_type"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_id"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_fit_score"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_due_date"), table_name="opportunities")
    op.drop_table("opportunities")

    op.drop_index(op.f("ix_ingestion_jobs_status"), table_name="ingestion_jobs")
    op.drop_index(op.f("ix_ingestion_jobs_id"), table_name="ingestion_jobs")
    op.drop_index(op.f("ix_ingestion_jobs_adapter"), table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")

    op.drop_index(op.f("ix_company_profiles_id"), table_name="company_profiles")
    op.drop_table("company_profiles")

