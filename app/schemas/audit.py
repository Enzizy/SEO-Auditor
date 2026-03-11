from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.audit_issue import IssueSeverity
from app.models.audit_run import AuditStatus


class AuditCreateForm(BaseModel):
    website_url: HttpUrl
    project_label: str = Field(min_length=2, max_length=255)
    max_pages: int = Field(default=25, ge=1, le=100)
    max_depth: int = Field(default=2, ge=0, le=5)
    pagespeed_strategy: Literal["mobile", "desktop"] = "mobile"
    js_render_mode: Literal["off", "auto", "on"] = "auto"
    external_link_check: bool = True

    @field_validator("project_label")
    @classmethod
    def normalize_label(cls, value: str) -> str:
        return value.strip()


class AuditStatusPayload(BaseModel):
    audit_id: int
    status: AuditStatus
    pages_crawled: int
    total_issues: int
    current_page_url: str | None = None
    progress_stage: str | None = None
    progress_message: str | None = None
    seo_score: float | None = None
    performance_score: float | None = None
    report_ready: bool = False
    error_message: str | None = None
    completed_at: datetime | None = None


class IssueSummary(BaseModel):
    id: int
    issue_type: str
    severity: IssueSeverity
    message: str
    recommendation: str
    page_url: str | None = None
