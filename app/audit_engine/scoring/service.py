from __future__ import annotations

from app.audit_engine.types import PageAnalysis, PageSpeedResult
from app.models.audit_issue import IssueSeverity


def calculate_scores(page_analyses: list[PageAnalysis], pagespeed_result: PageSpeedResult | None) -> tuple[float, float]:
    page_count = max(len(page_analyses), 1)
    critical = sum(1 for analysis in page_analyses for issue in analysis.issues if issue.severity == IssueSeverity.critical)
    warnings = sum(1 for analysis in page_analyses for issue in analysis.issues if issue.severity == IssueSeverity.warning)
    info = sum(1 for analysis in page_analyses for issue in analysis.issues if issue.severity == IssueSeverity.info)

    seo_penalty = ((critical * 8) + (warnings * 3) + info) / page_count
    seo_score = max(0.0, round(100 - seo_penalty, 1))

    asset_penalty = sum(
        2
        for analysis in page_analyses
        for issue in analysis.issues
        if issue.issue_type.startswith("large_") or issue.issue_type == "render_blocking_resource"
    )
    if pagespeed_result and pagespeed_result.score is not None:
        performance_score = max(0.0, round(pagespeed_result.score - min(asset_penalty, 20), 1))
    else:
        performance_score = max(0.0, round(85 - min(asset_penalty * 1.5, 40), 1))

    return seo_score, performance_score

