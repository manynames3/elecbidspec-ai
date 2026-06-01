"""public bid metadata

Revision ID: 0002_public_bid_metadata
Revises: 0001_initial
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_public_bid_metadata"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("source_type", sa.String(length=80), nullable=False, server_default="manual"))
    op.add_column("opportunities", sa.Column("bid_status", sa.String(length=40), nullable=False, server_default="open"))
    op.add_column("opportunities", sa.Column("value_confidence", sa.String(length=40), nullable=False, server_default="unknown"))
    op.add_column("opportunities", sa.Column("value_explanation", sa.Text(), nullable=True))
    op.add_column("opportunities", sa.Column("minimum_value_match", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    op.create_index(op.f("ix_opportunities_source_type"), "opportunities", ["source_type"], unique=False)
    op.create_index(op.f("ix_opportunities_bid_status"), "opportunities", ["bid_status"], unique=False)
    op.create_index(op.f("ix_opportunities_value_confidence"), "opportunities", ["value_confidence"], unique=False)
    op.create_index(op.f("ix_opportunities_minimum_value_match"), "opportunities", ["minimum_value_match"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_opportunities_minimum_value_match"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_value_confidence"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_bid_status"), table_name="opportunities")
    op.drop_index(op.f("ix_opportunities_source_type"), table_name="opportunities")

    op.drop_column("opportunities", "minimum_value_match")
    op.drop_column("opportunities", "value_explanation")
    op.drop_column("opportunities", "value_confidence")
    op.drop_column("opportunities", "bid_status")
    op.drop_column("opportunities", "source_type")
