from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.audit_issue import AuditIssue
    from app.models.page_audit_result import PageAuditResult
    from app.models.website_project import WebsiteProject


class AuditStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    website_id: Mapped[int] = mapped_column(ForeignKey("website_projects.id", ondelete="CASCADE"), index=True)
    start_url: Mapped[str] = mapped_column(String(500))
    status: Mapped[AuditStatus] = mapped_column(SqlEnum(AuditStatus), default=AuditStatus.queued, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    crawl_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    crawl_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analysis_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    analysis_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reporting_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reporting_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0)
    seo_score: Mapped[float | None]
    performance_score: Mapped[float | None]
    report_html_path: Mapped[str | None] = mapped_column(String(500))
    report_pdf_path: Mapped[str | None] = mapped_column(String(500))
    report_csv_path: Mapped[str | None] = mapped_column(String(500))
    pagespeed_strategy: Mapped[str] = mapped_column(String(32), default="mobile")
    max_pages: Mapped[int] = mapped_column(Integer, default=25)
    max_depth: Mapped[int] = mapped_column(Integer, default=2)
    js_render_mode: Mapped[str] = mapped_column(String(16), default="auto")
    external_link_check: Mapped[bool] = mapped_column(Boolean, default=True)
    current_page_url: Mapped[str | None] = mapped_column(String(500))
    progress_stage: Mapped[str | None] = mapped_column(String(64))
    progress_message: Mapped[str | None] = mapped_column(Text)
    total_issues: Mapped[int] = mapped_column(Integer, default=0)
    broken_links: Mapped[int] = mapped_column(Integer, default=0)
    missing_meta_descriptions: Mapped[int] = mapped_column(Integer, default=0)
    missing_alt_images: Mapped[int] = mapped_column(Integer, default=0)
    job_id: Mapped[str | None] = mapped_column(String(255), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)

    website: Mapped["WebsiteProject"] = relationship(back_populates="audit_runs")
    page_results: Mapped[list["PageAuditResult"]] = relationship(
        back_populates="audit_run", cascade="all, delete-orphan"
    )
    issues: Mapped[list["AuditIssue"]] = relationship(back_populates="audit_run", cascade="all, delete-orphan")
