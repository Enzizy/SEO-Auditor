"""add audit phase timestamps

Revision ID: 20260311_0003
Revises: 20260311_0002
Create Date: 2026-03-11 14:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260311_0003"
down_revision = "20260311_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("audit_runs", sa.Column("crawl_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("audit_runs", sa.Column("crawl_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("audit_runs", sa.Column("analysis_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("audit_runs", sa.Column("analysis_completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("audit_runs", sa.Column("reporting_started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("audit_runs", sa.Column("reporting_completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_runs", "reporting_completed_at")
    op.drop_column("audit_runs", "reporting_started_at")
    op.drop_column("audit_runs", "analysis_completed_at")
    op.drop_column("audit_runs", "analysis_started_at")
    op.drop_column("audit_runs", "crawl_completed_at")
    op.drop_column("audit_runs", "crawl_started_at")
