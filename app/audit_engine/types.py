from __future__ import annotations

from dataclasses import dataclass, field

from app.models.audit_issue import IssueSeverity


@dataclass(slots=True)
class LinkResource:
    url: str
    normalized_url: str
    is_internal: bool
    status_code: int | None = None


@dataclass(slots=True)
class ImageResource:
    url: str
    normalized_url: str
    alt_text: str | None
    width: int | None
    height: int | None
    size_bytes: int | None = None
    format: str | None = None


@dataclass(slots=True)
class AssetResource:
    url: str
    normalized_url: str
    asset_type: str
    size_bytes: int | None = None
    format: str | None = None


@dataclass(slots=True)
class CrawledPage:
    url: str
    normalized_url: str
    depth: int
    status_code: int | None
    html: str
    title: str | None
    meta_description: str | None
    h1_count: int
    word_count: int
    text_content: str
    links: list[LinkResource] = field(default_factory=list)
    images: list[ImageResource] = field(default_factory=list)
    assets: list[AssetResource] = field(default_factory=list)

    @property
    def internal_links_count(self) -> int:
        return sum(1 for link in self.links if link.is_internal)

    @property
    def external_links_count(self) -> int:
        return sum(1 for link in self.links if not link.is_internal)


@dataclass(slots=True)
class IssuePayload:
    issue_type: str
    severity: IssueSeverity
    message: str
    recommendation: str
    page_url: str | None = None


@dataclass(slots=True)
class PageAnalysis:
    page: CrawledPage
    issues: list[IssuePayload]
    keyword_density: list[tuple[str, float]]
    broken_internal_links: int = 0
    broken_external_links: int = 0
    pagespeed_score: float | None = None


@dataclass(slots=True)
class PageSpeedResult:
    url: str
    strategy: str
    score: float | None
    render_blocking_resources: list[str]
    opportunities: list[str]
    raw: dict


@dataclass(slots=True)
class AuditArtifacts:
    html_path: str
    pdf_path: str
    csv_path: str

