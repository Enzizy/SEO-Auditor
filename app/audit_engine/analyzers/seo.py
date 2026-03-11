from __future__ import annotations

from collections import Counter

from app.audit_engine.types import CrawledPage, IssuePayload, PageAnalysis
from app.audit_engine.utils.text import keyword_density
from app.models.audit_issue import IssueSeverity


def build_duplicate_sets(pages: list[CrawledPage]) -> tuple[set[str], set[str]]:
    title_counts = Counter(page.title.strip() for page in pages if page.title)
    meta_counts = Counter(page.meta_description.strip() for page in pages if page.meta_description)
    duplicate_titles = {title for title, count in title_counts.items() if count > 1}
    duplicate_descriptions = {meta for meta, count in meta_counts.items() if count > 1}
    return duplicate_titles, duplicate_descriptions


def analyze_page_seo(
    page: CrawledPage,
    duplicate_titles: set[str],
    duplicate_descriptions: set[str],
) -> PageAnalysis:
    issues: list[IssuePayload] = []

    if not page.title:
        issues.append(
            IssuePayload(
                issue_type="missing_title",
                severity=IssueSeverity.critical,
                message="Page is missing a title tag.",
                recommendation="Add a unique title tag under 60 characters.",
                page_url=page.url,
            )
        )
    elif page.title in duplicate_titles:
        issues.append(
            IssuePayload(
                issue_type="duplicate_title",
                severity=IssueSeverity.warning,
                message="Title tag is duplicated across crawled pages.",
                recommendation="Rewrite titles so each page targets a distinct search intent.",
                page_url=page.url,
            )
        )

    if not page.meta_description:
        issues.append(
            IssuePayload(
                issue_type="missing_meta_description",
                severity=IssueSeverity.warning,
                message="Page is missing a meta description.",
                recommendation="Add a descriptive meta description between 120 and 160 characters.",
                page_url=page.url,
            )
        )
    elif page.meta_description in duplicate_descriptions:
        issues.append(
            IssuePayload(
                issue_type="duplicate_meta_description",
                severity=IssueSeverity.warning,
                message="Meta description is duplicated across crawled pages.",
                recommendation="Give each page a unique meta description with page-specific copy.",
                page_url=page.url,
            )
        )

    if page.h1_count == 0:
        issues.append(
            IssuePayload(
                issue_type="missing_h1",
                severity=IssueSeverity.warning,
                message="Page does not contain an H1 heading.",
                recommendation="Add one descriptive H1 that matches the page topic.",
                page_url=page.url,
            )
        )
    elif page.h1_count > 1:
        issues.append(
            IssuePayload(
                issue_type="multiple_h1",
                severity=IssueSeverity.info,
                message="Page has multiple H1 headings.",
                recommendation="Keep a single primary H1 unless the template structure clearly requires otherwise.",
                page_url=page.url,
            )
        )

    broken_internal = sum(1 for link in page.links if link.is_internal and link.status_code and link.status_code >= 400)
    broken_external = sum(1 for link in page.links if not link.is_internal and link.status_code and link.status_code >= 400)

    if broken_internal:
        issues.append(
            IssuePayload(
                issue_type="broken_internal_links",
                severity=IssueSeverity.critical,
                message=f"Detected {broken_internal} broken internal link(s).",
                recommendation="Fix internal links or redirect them to valid pages.",
                page_url=page.url,
            )
        )
    if broken_external:
        issues.append(
            IssuePayload(
                issue_type="broken_external_links",
                severity=IssueSeverity.warning,
                message=f"Detected {broken_external} broken external link(s).",
                recommendation="Replace or remove broken outbound links.",
                page_url=page.url,
            )
        )

    return PageAnalysis(
        page=page,
        issues=issues,
        keyword_density=keyword_density(page.text_content),
        broken_internal_links=broken_internal,
        broken_external_links=broken_external,
    )

