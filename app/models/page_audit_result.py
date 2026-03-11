from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.asset_record import AssetRecord
    from app.models.audit_issue import AuditIssue
    from app.models.audit_run import AuditRun


class PageAuditResult(Base):
    __tablename__ = "page_audit_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    audit_run_id: Mapped[int] = mapped_column(ForeignKey("audit_runs.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(500), index=True)
    status_code: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str | None] = mapped_column(String(500))
    meta_description: Mapped[str | None] = mapped_column(Text)
    h1_count: Mapped[int] = mapped_column(Integer, default=0)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    internal_links_count: Mapped[int] = mapped_column(Integer, default=0)
    external_links_count: Mapped[int] = mapped_column(Integer, default=0)
    broken_links_count: Mapped[int] = mapped_column(Integer, default=0)
    pagespeed_score: Mapped[float | None] = mapped_column(Float)
    issues_count: Mapped[int] = mapped_column(Integer, default=0)
    missing_alt_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    audit_run: Mapped["AuditRun"] = relationship(back_populates="page_results")
    issues: Mapped[list["AuditIssue"]] = relationship(back_populates="page_result")
    assets: Mapped[list["AssetRecord"]] = relationship(back_populates="page_result", cascade="all, delete-orphan")
