from __future__ import annotations

from app.audit_engine.types import CrawledPage, IssuePayload, PageSpeedResult
from app.config import get_settings
from app.models.audit_issue import IssueSeverity


def analyze_page_assets(page: CrawledPage) -> list[IssuePayload]:
    settings = get_settings()
    issues: list[IssuePayload] = []
    for asset in page.assets:
        if asset.size_bytes and asset.size_bytes > settings.large_asset_bytes:
            issues.append(
                IssuePayload(
                    issue_type=f"large_{asset.asset_type}_asset",
                    severity=IssueSeverity.warning,
                    message=f"Large {asset.asset_type} asset detected: {asset.url}",
                    recommendation="Reduce bundle size, defer unused assets, or split assets by page intent.",
                    page_url=page.url,
                )
            )
    return issues


def analyze_pagespeed(result: PageSpeedResult | None) -> list[IssuePayload]:
    if result is None:
        return []
    issues: list[IssuePayload] = []
    if result.score is not None and result.score < 60:
        issues.append(
            IssuePayload(
                issue_type="low_pagespeed_score",
                severity=IssueSeverity.warning,
                message=f"Homepage PageSpeed score is {result.score:.0f}.",
                recommendation="Improve render path, reduce blocking JS/CSS, and optimize media delivery.",
                page_url=result.url,
            )
        )
    for resource in result.render_blocking_resources[:10]:
        issues.append(
            IssuePayload(
                issue_type="render_blocking_resource",
                severity=IssueSeverity.info,
                message=f"Render-blocking resource reported by PageSpeed: {resource}",
                recommendation="Inline critical CSS, defer non-critical assets, or preload strategically.",
                page_url=result.url,
            )
        )
    return issues

