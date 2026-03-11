"""add audit progress fields

Revision ID: 20260311_0002
Revises: 20260311_0001
Create Date: 2026-03-11 14:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260311_0002"
down_revision = "20260311_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_runs", sa.Column("progress_stage", sa.String(length=64), nullable=True))
    op.add_column("audit_runs", sa.Column("progress_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_runs", "progress_message")
    op.drop_column("audit_runs", "progress_stage")
