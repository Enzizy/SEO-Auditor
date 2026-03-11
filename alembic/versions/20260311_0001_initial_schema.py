"""initial schema

Revision ID: 20260311_0001
Revises:
Create Date: 2026-03-11 12:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260311_0001"
down_revision = None
branch_labels = None
depends_on = None


audit_status = sa.Enum("queued", "running", "completed", "failed", name="auditstatus")
issue_severity = sa.Enum("critical", "warning", "info", name="issueseverity")


def upgrade() -> None:
    bind = op.get_bind()
    audit_status.create(bind, checkfirst=True)
    issue_severity.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "website_projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_website_projects_user_id", "website_projects", ["user_id"], unique=False)
    op.create_index("ix_website_projects_domain", "website_projects", ["domain"], unique=False)

    op.create_table(
        "audit_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("website_id", sa.Integer(), nullable=False),
        sa.Column("start_url", sa.String(length=500), nullable=False),
        sa.Column("status", audit_status, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("pages_crawled", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("seo_score", sa.Float(), nullable=True),
        sa.Column("performance_score", sa.Float(), nullable=True),
        sa.Column("report_html_path", sa.String(length=500), nullable=True),
        sa.Column("report_pdf_path", sa.String(length=500), nullable=True),
        sa.Column("report_csv_path", sa.String(length=500), nullable=True),
        sa.Column("pagespeed_strategy", sa.String(length=32), nullable=False, server_default="mobile"),
        sa.Column("max_pages", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("max_depth", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("js_render_mode", sa.String(length=16), nullable=False, server_default="auto"),
        sa.Column("external_link_check", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("current_page_url", sa.String(length=500), nullable=True),
        sa.Column("total_issues", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("broken_links", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_meta_descriptions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_alt_images", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("job_id", sa.String(length=255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["website_id"], ["website_projects.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_audit_runs_website_id", "audit_runs", ["website_id"], unique=False)
    op.create_index("ix_audit_runs_status", "audit_runs", ["status"], unique=False)
    op.create_index("ix_audit_runs_created_at", "audit_runs", ["created_at"], unique=False)
    op.create_index("ix_audit_runs_job_id", "audit_runs", ["job_id"], unique=False)

    op.create_table(
        "page_audit_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("audit_run_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("h1_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("internal_links_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("external_links_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("broken_links_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pagespeed_score", sa.Float(), nullable=True),
        sa.Column("issues_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_alt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_page_audit_results_audit_run_id", "page_audit_results", ["audit_run_id"], unique=False)
    op.create_index("ix_page_audit_results_url", "page_audit_results", ["url"], unique=False)

    op.create_table(
        "audit_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("audit_run_id", sa.Integer(), nullable=False),
        sa.Column("page_result_id", sa.Integer(), nullable=True),
        sa.Column("issue_type", sa.String(length=120), nullable=False),
        sa.Column("severity", issue_severity, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["audit_run_id"], ["audit_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["page_result_id"], ["page_audit_results.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_issues_audit_run_id", "audit_issues", ["audit_run_id"], unique=False)
    op.create_index("ix_audit_issues_issue_type", "audit_issues", ["issue_type"], unique=False)
    op.create_index("ix_audit_issues_severity", "audit_issues", ["severity"], unique=False)

    op.create_table(
        "asset_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("page_result_id", sa.Integer(), nullable=False),
        sa.Column("asset_url", sa.String(length=500), nullable=False),
        sa.Column("asset_type", sa.String(length=50), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(length=32), nullable=True),
        sa.Column("is_optimized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("compression_suggestion", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["page_result_id"], ["page_audit_results.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_asset_records_page_result_id", "asset_records", ["page_result_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_asset_records_page_result_id", table_name="asset_records")
    op.drop_table("asset_records")
    op.drop_index("ix_audit_issues_severity", table_name="audit_issues")
    op.drop_index("ix_audit_issues_issue_type", table_name="audit_issues")
    op.drop_index("ix_audit_issues_audit_run_id", table_name="audit_issues")
    op.drop_table("audit_issues")
    op.drop_index("ix_page_audit_results_url", table_name="page_audit_results")
    op.drop_index("ix_page_audit_results_audit_run_id", table_name="page_audit_results")
    op.drop_table("page_audit_results")
    op.drop_index("ix_audit_runs_job_id", table_name="audit_runs")
    op.drop_index("ix_audit_runs_created_at", table_name="audit_runs")
    op.drop_index("ix_audit_runs_status", table_name="audit_runs")
    op.drop_index("ix_audit_runs_website_id", table_name="audit_runs")
    op.drop_table("audit_runs")
    op.drop_index("ix_website_projects_domain", table_name="website_projects")
    op.drop_index("ix_website_projects_user_id", table_name="website_projects")
    op.drop_table("website_projects")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    bind = op.get_bind()
    issue_severity.drop(bind, checkfirst=True)
    audit_status.drop(bind, checkfirst=True)
