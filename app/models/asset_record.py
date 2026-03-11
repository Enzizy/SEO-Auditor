from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.page_audit_result import PageAuditResult


class AssetRecord(Base):
    __tablename__ = "asset_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_result_id: Mapped[int] = mapped_column(ForeignKey("page_audit_results.id", ondelete="CASCADE"), index=True)
    asset_url: Mapped[str] = mapped_column(String(500))
    asset_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    format: Mapped[str | None] = mapped_column(String(32))
    is_optimized: Mapped[bool] = mapped_column(Boolean, default=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    compression_suggestion: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP"))

    page_result: Mapped["PageAuditResult"] = relationship(back_populates="assets")
