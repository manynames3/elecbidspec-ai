"""workflow alerts proposal cache and document intelligence

Revision ID: 0004_workflow_alerts_documents
Revises: 0003_auth_and_tenants
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_workflow_alerts_documents"
down_revision = "0003_auth_and_tenants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opportunity_workflows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=80), nullable=False, server_default="default"),
        sa.Column("saved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("watched", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="reviewing"),
        sa.Column("owner", sa.String(length=160), nullable=True),
        sa.Column("priority", sa.String(length=40), nullable=False, server_default="normal"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opportunity_id", "tenant_id", name="uq_opportunity_workflow_tenant"),
    )
    op.create_index(op.f("ix_opportunity_workflows_hidden"), "opportunity_workflows", ["hidden"], unique=False)
    op.create_index(op.f("ix_opportunity_workflows_id"), "opportunity_workflows", ["id"], unique=False)
    op.create_index(op.f("ix_opportunity_workflows_opportunity_id"), "opportunity_workflows", ["opportunity_id"], unique=False)
    op.create_index(op.f("ix_opportunity_workflows_priority"), "opportunity_workflows", ["priority"], unique=False)
    op.create_index(op.f("ix_opportunity_workflows_saved"), "opportunity_workflows", ["saved"], unique=False)
    op.create_index(op.f("ix_opportunity_workflows_status"), "opportunity_workflows", ["status"], unique=False)
    op.create_index(op.f("ix_opportunity_workflows_tenant_id"), "opportunity_workflows", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_opportunity_workflows_watched"), "opportunity_workflows", ["watched"], unique=False)

    op.create_table(
        "proposal_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=80), nullable=False, server_default="default"),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="deterministic"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="ready"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opportunity_id", "tenant_id", name="uq_proposal_artifact_tenant"),
    )
    op.create_index(op.f("ix_proposal_artifacts_id"), "proposal_artifacts", ["id"], unique=False)
    op.create_index(op.f("ix_proposal_artifacts_opportunity_id"), "proposal_artifacts", ["opportunity_id"], unique=False)
    op.create_index(op.f("ix_proposal_artifacts_source"), "proposal_artifacts", ["source"], unique=False)
    op.create_index(op.f("ix_proposal_artifacts_status"), "proposal_artifacts", ["status"], unique=False)
    op.create_index(op.f("ix_proposal_artifacts_tenant_id"), "proposal_artifacts", ["tenant_id"], unique=False)

    op.create_table(
        "alert_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=80), nullable=False, server_default="default"),
        sa.Column("email_to", sa.String(length=255), nullable=True),
        sa.Column("min_fit_score", sa.Integer(), nullable=False, server_default="70"),
        sa.Column("due_within_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("include_source_failures", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", name="uq_alert_preferences_tenant"),
    )
    op.create_index(op.f("ix_alert_preferences_enabled"), "alert_preferences", ["enabled"], unique=False)
    op.create_index(op.f("ix_alert_preferences_id"), "alert_preferences", ["id"], unique=False)
    op.create_index(op.f("ix_alert_preferences_tenant_id"), "alert_preferences", ["tenant_id"], unique=False)

    op.create_table(
        "alert_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=80), nullable=False, server_default="default"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="complete"),
        sa.Column("digest", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("sent_to", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alert_runs_id"), "alert_runs", ["id"], unique=False)
    op.create_index(op.f("ix_alert_runs_status"), "alert_runs", ["status"], unique=False)
    op.create_index(op.f("ix_alert_runs_tenant_id"), "alert_runs", ["tenant_id"], unique=False)

    op.create_table(
        "opportunity_attachment_extractions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("opportunity_id", sa.Integer(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("filename", sa.String(length=260), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("attachment", sa.JSON(), nullable=False),
        sa.Column("extracted_specs", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("opportunity_id", "source_url", name="uq_attachment_extraction_source"),
    )
    op.create_index(op.f("ix_opportunity_attachment_extractions_id"), "opportunity_attachment_extractions", ["id"], unique=False)
    op.create_index(
        op.f("ix_opportunity_attachment_extractions_opportunity_id"),
        "opportunity_attachment_extractions",
        ["opportunity_id"],
        unique=False,
    )
    op.create_index(op.f("ix_opportunity_attachment_extractions_status"), "opportunity_attachment_extractions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_opportunity_attachment_extractions_status"), table_name="opportunity_attachment_extractions")
    op.drop_index(op.f("ix_opportunity_attachment_extractions_opportunity_id"), table_name="opportunity_attachment_extractions")
    op.drop_index(op.f("ix_opportunity_attachment_extractions_id"), table_name="opportunity_attachment_extractions")
    op.drop_table("opportunity_attachment_extractions")

    op.drop_index(op.f("ix_alert_runs_tenant_id"), table_name="alert_runs")
    op.drop_index(op.f("ix_alert_runs_status"), table_name="alert_runs")
    op.drop_index(op.f("ix_alert_runs_id"), table_name="alert_runs")
    op.drop_table("alert_runs")

    op.drop_index(op.f("ix_alert_preferences_tenant_id"), table_name="alert_preferences")
    op.drop_index(op.f("ix_alert_preferences_id"), table_name="alert_preferences")
    op.drop_index(op.f("ix_alert_preferences_enabled"), table_name="alert_preferences")
    op.drop_table("alert_preferences")

    op.drop_index(op.f("ix_proposal_artifacts_tenant_id"), table_name="proposal_artifacts")
    op.drop_index(op.f("ix_proposal_artifacts_status"), table_name="proposal_artifacts")
    op.drop_index(op.f("ix_proposal_artifacts_source"), table_name="proposal_artifacts")
    op.drop_index(op.f("ix_proposal_artifacts_opportunity_id"), table_name="proposal_artifacts")
    op.drop_index(op.f("ix_proposal_artifacts_id"), table_name="proposal_artifacts")
    op.drop_table("proposal_artifacts")

    op.drop_index(op.f("ix_opportunity_workflows_watched"), table_name="opportunity_workflows")
    op.drop_index(op.f("ix_opportunity_workflows_tenant_id"), table_name="opportunity_workflows")
    op.drop_index(op.f("ix_opportunity_workflows_status"), table_name="opportunity_workflows")
    op.drop_index(op.f("ix_opportunity_workflows_saved"), table_name="opportunity_workflows")
    op.drop_index(op.f("ix_opportunity_workflows_priority"), table_name="opportunity_workflows")
    op.drop_index(op.f("ix_opportunity_workflows_opportunity_id"), table_name="opportunity_workflows")
    op.drop_index(op.f("ix_opportunity_workflows_id"), table_name="opportunity_workflows")
    op.drop_index(op.f("ix_opportunity_workflows_hidden"), table_name="opportunity_workflows")
    op.drop_table("opportunity_workflows")
