"""saved searches

Revision ID: 0005_saved_searches
Revises: 0004_workflow_alerts_documents
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0005_saved_searches"
down_revision = "0004_workflow_alerts_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "saved_searches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=80), nullable=False, server_default="default"),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("query", sa.Text(), nullable=True),
        sa.Column("filters", sa.JSON(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("email_digest", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_saved_search_tenant_name"),
    )
    op.create_index(op.f("ix_saved_searches_email_digest"), "saved_searches", ["email_digest"], unique=False)
    op.create_index(op.f("ix_saved_searches_enabled"), "saved_searches", ["enabled"], unique=False)
    op.create_index(op.f("ix_saved_searches_id"), "saved_searches", ["id"], unique=False)
    op.create_index(op.f("ix_saved_searches_name"), "saved_searches", ["name"], unique=False)
    op.create_index(op.f("ix_saved_searches_tenant_id"), "saved_searches", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_saved_searches_tenant_id"), table_name="saved_searches")
    op.drop_index(op.f("ix_saved_searches_name"), table_name="saved_searches")
    op.drop_index(op.f("ix_saved_searches_id"), table_name="saved_searches")
    op.drop_index(op.f("ix_saved_searches_enabled"), table_name="saved_searches")
    op.drop_index(op.f("ix_saved_searches_email_digest"), table_name="saved_searches")
    op.drop_table("saved_searches")
