from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.audit_run import AuditRun
    from app.models.page_audit_result import PageAuditResult


class IssueSeverity(str, Enum):
    critical = "critical"
    warning = "warning"
    info = "info"


class AuditIssue(Base):
    __tablename__ = "audit_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    audit_run_id: Mapped[int] = mapped_column(ForeignKey("audit_runs.id", ondelete="CASCADE"), index=True)
    page_result_id: Mapped[int | None] = mapped_column(ForeignKey("page_audit_results.id", ondelete="SET NULL"))
    issue_type: Mapped[str] = mapped_column(String(120), index=True)
    severity: Mapped[IssueSeverity] = mapped_column(SqlEnum(IssueSeverity), default=IssueSeverity.warning, index=True)
    message: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    audit_run: Mapped["AuditRun"] = relationship(back_populates="issues")
    page_result: Mapped["PageAuditResult | None"] = relationship(back_populates="issues")
